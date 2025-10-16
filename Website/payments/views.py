from inspect import stack
import json
import time
import stripe
from stripe import error as stripe_error
import random
import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from typing import Union

from core.decorators import oauth_required, AuthHttpRequest
import stacks.services as stack_services
from stacks.models import PurchasableStack, StackDatabase, Stack
from organizations.models import Organization
from organizations.services import get_organization
from accounts.models import UserProfile
from core.helpers import request_helpers
from projects.models import Project
from payments.models import (
    Account, Product, Meter, UsageEvent, Charge, ChargeSource, Currency
)
from decimal import Decimal

stripe.api_key = settings.STRIPE.get("SECRET_KEY")


def stripe_config(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        # Handle non-GET requests
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)
    stripe_config = {"public_key": STRIPE_PUBLISHABLE_KEY}
    return JsonResponse(stripe_config, status=200)


def save_stripe_payment_method(request: AuthHttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    try:
        data = json.loads(request.body)
        payment_method_id = data.get("payment_method_id")
        organization_id = data.get(
            "organization_id"
        )  # Assuming organizationId is used as customerId

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        print(
            f"Payment Method ID: {payment_method_id}, Customer ID: {customer_id}",
            "Organization ID:",
            organization_id,
        )

        if not payment_method_id or not customer_id:
            return JsonResponse(
                {"error": "Missing paymentMethodId or customerId"}, status=400
            )

        # Attach the payment method to the customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id,
        )

        # Set the payment method as the default for the customer
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        return JsonResponse(
            {"message": "Payment method saved successfully."}, status=200
        )

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)

    except Exception as e:
        return JsonResponse(
            {"error": f"An error occurred while saving the payment method: {e}"}, status=400
        )

def create_payment_intent(request: AuthHttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    try:
        data = json.loads(request.body)
        organization_id = data.get("organization_id")

        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Create a SetupIntent for adding payment methods without charging
        setup_intent = stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=["card"],
            usage="off_session",  # This allows the payment method to be used for future payments
        )

        return JsonResponse({
            "client_secret": setup_intent.client_secret,
            "setup_intent_id": setup_intent.id
        }, status=200)

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": f"An error occurred while creating the setup intent: {e}"}, status=400
        )


@oauth_required()
def create_checkout_session(request: AuthHttpRequest, org_id: str) -> JsonResponse:
    auth_user = request.auth_user

    if not org_id:
        return JsonResponse({"error": "Organization ID is required"}, status=400)

    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    domain_url = settings.HOST

    try:
        stack_id, project_id = request_helpers.assertRequestFields(
            request, ["stack_id", "project_id"]
        )
    except request_helpers.MissingFieldError as e:
        return e.to_response()

    organization = get_organization(auth_user, org_id)

    if not organization:
        return JsonResponse({"error": "Organization not found"}, status=404)

    purchasable_stack = PurchasableStack.objects.get(id=stack_id)
    price_id = purchasable_stack.price_id

    try:
        # Check if the price is free (amount = 0)
        price = stripe.Price.retrieve(price_id)
        is_free = price.unit_amount == 0
        
        # Ensure organization has a Stripe customer ID
        if not organization.stripe_customer_id:
            # Create a new Stripe customer for the organization
            customer = stripe.Customer.create(
                email=organization.email,
                name=organization.name,
                metadata={
                    "organization_id": organization.id,
                }
            )
            organization.stripe_customer_id = customer.id
            organization.save()
        
        has_payment_method, _ = check_organization_payment_methods(organization)

        if is_free and not has_payment_method:
            # Use setup mode for free stacks
            checkout_session = stripe.checkout.Session.create(
                metadata={
                    "purchasable_stack_id": stack_id,
                    "organization_id": organization.id,
                    "project_id": project_id,
                },
                customer=organization.stripe_customer_id,
                success_url=domain_url
                + "/payments/checkout/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "/payments/cancelled",
                payment_method_types=["card"],
                mode="setup",
            )
        else:
            # Use payment mode for paid stacks
            checkout_session = stripe.checkout.Session.create(
                metadata={
                    "purchasable_stack_id": stack_id,
                    "organization_id": organization.id,
                    "project_id": project_id,
                },
                customer=organization.stripe_customer_id,
                success_url=domain_url
                + "/payments/checkout/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "/payments/cancelled",
                payment_method_types=["card"],
                mode="payment",
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                payment_intent_data={
                    "setup_future_usage": "off_session",  # This tells Stripe to save the card for future payments
                },
            )
        return JsonResponse({"sessionId": checkout_session["id"]})
    except Exception as e:
        return JsonResponse({"error": str(e)})


def record_usage(subscription_item_id, quantity):
    try:
        stripe.UsageRecord.create(
            subscription_item=subscription_item_id,
            quantity=quantity,  # Number of resources consumed
            timestamp=int(time.time()),  # Current timestamp
            action="increment",  # Add usage incrementally
        )
    except Exception as e:
        print(f"Error recording usage: {e}")


def stripe_webhook(request: HttpRequest) -> Union[HttpResponse, JsonResponse]:
    # Use `stripe listen --forward-to http://127.0.0.1:8000/api/v1/payments/webhook/` to listen for events
    WEBHOOK_SECRET = settings.STRIPE.get("WEBHOOK_SECRET", None)

    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError as e:
        # Invalid payload
        print(f"Error parsing webhook payload: {e}")
        return HttpResponse("Invalid payload", status=400)
    except stripe_error.SignatureVerificationError as e:  # type: ignore
        # Invalid signature
        print(f"Error verifying signature: {e}")
        return HttpResponse("Invalid signature", status=400)

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        metadata = session.get("metadata", {})

        purchasable_stack_id = metadata.get("purchasable_stack_id")
        project_id = metadata.get("project_id")
        organization_id = metadata.get("organization_id")

        # Fetch the user based on the Stripe Customer ID
        organization = get_object_or_404(Organization, id=organization_id)

        project = get_object_or_404(Project, id=project_id, organization=organization)

        purchased_stack = get_object_or_404(PurchasableStack, id=purchasable_stack_id)

        list_of_adjectives = [
            "Superb",
            "Incredible",
            "Fantastic",
            "Amazing",
            "Awesome",
            "Brilliant",
            "Exceptional",
            "Outstanding",
            "Remarkable",
            "Extraordinary",
            "Magnificent",
            "Spectacular",
            "Stunning",
            "Impressive",
        ]

        list_of_nouns = [
            "Stack",
            "Project",
            "Application",
            "Service",
            "Solution",
            "Platform",
            "System",
            "Framework",
            "Architecture",
            "Design",
            "Model",
            "Structure",
            "Configuration",
        ]

        # Generate a random name for the stack
        random_adjective = random.choice(list_of_adjectives)
        random_noun = random.choice(list_of_nouns)
        random_name = f"{random_adjective} {random_noun}"

        # Create a stack entry for the user
        stack_services.add_stack(
            name=random_name,
            project_id=project.id,
            purchasable_stack_id=purchased_stack.id,
        )

    return HttpResponse(status=200)


def create_invoice(customer_id, dollar_amount, description) -> str:
    try:
        # Step 1: Create an invoice item
        stripe.InvoiceItem.create(
            customer=customer_id,
            amount=int(100 * dollar_amount),
            currency="usd",  # You can change the currency if needed
            description=description,
        )

        # Step 2: Create the invoice for the customer
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=False,  # Automatically finalizes and sends the invoice
        )

        # Step 3: Finalize the invoice (send to customer)
        invoice.finalize_invoice()

        return invoice.id, invoice.hosted_invoice_url

    except stripe_error.StripeError as e:  # type: ignore
        print(f"Error creating invoice: {e}")
        return None

    except Exception as e:
        print(f"Error creating invoice: {e}")
        return None


def get_customer_id(org_id):
    # Query the Organization by the provided org_id
    try:
        org = Organization.objects.get(id=org_id)
        customer_id = org.stripe_customer_id

        return customer_id

    except Organization.DoesNotExist:
        return None


def check_organization_payment_methods(organization):
    """
    Check if an organization has payment methods set up.
    Returns a tuple: (has_payment_methods, error_message)
    """
    if not organization.stripe_customer_id:
        # Create a new Stripe customer for the organization
        try:
            customer = stripe.Customer.create(
                email=organization.email,
                name=organization.name,
                metadata={
                    "organization_id": organization.id,
                }
            )
            organization.stripe_customer_id = customer.id
            organization.save()
            return False, "No payment methods found for this organization. Please add a payment method before making purchases."
        except Exception as e:
            return False, f"Error creating payment account: {str(e)}"
    
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=organization.stripe_customer_id,
            type="card"
        )
        
        if not payment_methods.data:
            return False, "No payment methods found for this organization. Please add a payment method before making purchases."
            
        return True, None
        
    except stripe_error.StripeError as e:
        return False, f"Error checking payment methods: {str(e)}"
    except Exception as e:
        return False, "An error occurred while checking payment methods."


def update_invoice_billing(request):
    if request.method == "POST":
        data = json.loads(request.body)
        stack_id = data.get("stack_id")
        cost = data.get("cost")
        updated_count = StackDatabase.objects.filter(stack_id=stack_id).update(
            current_usage=0
        )
        # billing = StackDatabase.objects.filter(stack_id=stack_id).update(
        #     pending_billed=F("pending_billed") + cost
        # )

        # Check if any rows were updated
        if updated_count > 0:
            # Successfully updated
            return JsonResponse(
                {"message": "Invoice billing updated successfully."}, status=200
            )
        else:
            # Failed to update (either no such stack_id or no change made)
            return JsonResponse(
                {"error": "Stack ID not found or already updated."}, status=400
            )


# @oauth_required()
# def create_price_item(request: HttpRequest) -> JsonResponse:
#     return pricing_services.create_price_item(request)


# @oauth_required()
# def update_price_item(request: HttpRequest) -> JsonResponse:
#     return pricing_services.update_price_item(request)


# @oauth_required()
# def delete_price_item(request: HttpRequest) -> JsonResponse:
#     return pricing_services.delete_price_item(request)


# @oauth_required()
# def get_price_item_by_name(request: HttpRequest, name: str) -> JsonResponse:
#     return pricing_services.get_price_item_by_name(request, name)


def get_payment_method(request: HttpRequest, org_id: str) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    try:
        if not org_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=org_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Retrieve the customer's default payment method
        customer = stripe.Customer.retrieve(
            customer_id, expand=["invoice_settings.default_payment_method"]
        )

        if not customer:
            return JsonResponse({"error": "No customer found"}, status=404)

        if not customer.invoice_settings:
            return JsonResponse({"error": "Invoice settings not found"}, status=404)

        default_payment_method_id = customer.invoice_settings.default_payment_method  # type: ignore

        if not default_payment_method_id:
            return JsonResponse({"error": "No payment method found"}, status=404)

        # Format the card information
        card_info = {
            "brand": default_payment_method_id.card.brand,  # type: ignore
            "last4": default_payment_method_id.card.last4,  # type: ignore
            "exp_month": default_payment_method_id.card.exp_month,  # type: ignore
            "exp_year": default_payment_method_id.card.exp_year,  # type: ignore
        }

        return JsonResponse(card_info, status=200)

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while retrieving the payment method."},
            status=400,
        )


def get_all_payment_methods(request: HttpRequest, org_id: str) -> JsonResponse:
    """Get all payment methods for an organization."""
    if request.method != "GET":
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    try:
        if not org_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=org_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Get all payment methods for the customer
        payment_methods = stripe.PaymentMethod.list(customer=customer_id, type="card")

        # Get the customer to find the default payment method
        customer = stripe.Customer.retrieve(customer_id)
        default_payment_method_id = customer.invoice_settings.default_payment_method if customer.invoice_settings else None

        # Format all payment methods
        formatted_methods = []
        for pm in payment_methods.data:
            if pm.card:  # Check if card exists
                formatted_methods.append({
                    "id": pm.id,
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year,
                    "is_default": pm.id == default_payment_method_id,
                })

        return JsonResponse({"payment_methods": formatted_methods}, status=200)

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while retrieving payment methods."},
            status=400,
        )


def delete_payment_method(request: HttpRequest) -> JsonResponse:
    if request.method != "DELETE":
        return JsonResponse(
            {"error": "Invalid request method. Only DELETE is allowed."}, status=405
        )

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Get all payment methods for the customer
        payment_methods = stripe.PaymentMethod.list(customer=customer_id, type="card")

        if len(payment_methods.data) <= 1:
            return JsonResponse(
                {
                    "error": "Cannot remove the only payment method. Please add another payment method first."
                },
                status=400,
            )

        payment_method_id = request.GET.get("payment_method_id")
        if not payment_method_id:
            return JsonResponse({"error": "payment_method_id is required"}, status=400)

        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        if not payment_method:
            return JsonResponse({"error": "Payment method not found"}, status=404)

        customer = stripe.Customer.retrieve(customer_id)
        print(customer)
        default_payment_method_id = customer.invoice_settings.default_payment_method if customer.invoice_settings else None

        if default_payment_method_id:
            # Detach the payment method
            stripe.PaymentMethod.detach(default_payment_method_id)

            # Set the next available payment method as default
            if payment_methods.data:
                next_payment_method = next(
                    (
                        pm
                        for pm in payment_methods.data
                        if pm.id != default_payment_method_id
                    ),
                    None,
                )
                if next_payment_method:
                    stripe.Customer.modify(
                        customer_id,
                        invoice_settings={
                            "default_payment_method": next_payment_method.id
                        },
                    )

        else:
            stripe.PaymentMethod.detach(payment_method_id)

        return JsonResponse(
            {"message": "Payment method removed successfully."}, status=200
        )

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while removing the payment method."},
            status=400,
        )


def set_default_payment_method(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        payment_method_id = request.GET.get("payment_method_id")
        if not payment_method_id:
            return JsonResponse({"error": "payment_method_id is required"}, status=400)

        # Verify the payment method exists and belongs to the customer
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        if not payment_method or payment_method.customer != customer_id:
            return JsonResponse({"error": "Payment method not found or doesn't belong to this customer"}, status=404)

        # Set the payment method as default for the customer
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        return JsonResponse(
            {"message": "Default payment method updated successfully."}, status=200
        )

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while setting the default payment method."},
            status=400,
        )


def update_organization_usage(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":

        data = json.loads(request.body)
        return JsonResponse({"message": "Usage updated successfully."}, status=200)
    else:
        return JsonResponse({"error": "Invalid request method."}, status=405)

import os
import requests

def send_to_azure_function(message_data: dict, function_url: str | None = None) -> bool:
    """
    Sends a message to Azure Function via HTTP trigger.
    
    Args:
        message_data (dict): The data to send as a message
        function_url (str): The URL of the Azure Function HTTP trigger
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    function_url = function_url or os.environ.get('AZURE_FUNCTION_URL')

    if not function_url:
        logger.error("Azure Function URL is not configured.")
        return False

    try:
        # Send HTTP POST request to Azure Function
        response = requests.post(
            function_url,
            json=message_data,
            headers={'Content-Type': 'application/json'},
            timeout=30  # 30 second timeout
        )
        
        # Check if the request was successful
        if response.status_code in [200, 202]:
            logger.info(f"Successfully sent message to Azure Function: {function_url}")
            return True
        else:
            logger.error(f"Azure Function returned status code {response.status_code}: {response.text}")
            return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to Azure Function: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message to Azure Function: {str(e)}")
        return False
    

def get_billing_info(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        # Get all stacks
        stacks = Stack.objects.all()

        # Put request on Azure Service Bus
        message_data = {
            "request_type": "iac.billing",
            "source": os.environ.get("HOST"),          
            "data": {
                "stack_ids": [str(stack.id) for stack in stacks]
            }
        }

        # Send message to Azure Function (non-blocking)
        try:
            send_to_azure_function(message_data)
        except Exception as e:
            logger.warning(f"Failed to send message to Azure Function: {str(e)}")

    return JsonResponse({"error": "Invalid request method."}, status=405)

def _process_stack_billing(stack_id: str, cost_str: str, infrastructure_product: Product, daily_cost_meter: Meter, today) -> tuple:
    """
    Process billing information for a single stack.
    Returns tuple of (usage_event_id, charge_id) or (None, None) if processing failed.
    """
    try:
        # Get the stack
        stack = Stack.objects.get(id=stack_id)
        
        # Get or create account for the stack's organization
        account, _ = Account.objects.get_or_create(
            organization=stack.project.organization,
            defaults={
                "name": f"{stack.project.organization.name} Account",
                "email_billing": stack.project.organization.email,
                "currency": Currency.USD
            }
        )
        
        # Convert cost to decimal (assuming it comes as string)
        cost_decimal = Decimal(str(cost_str))
        
        # Create usage event for the infrastructure cost
        usage_event = UsageEvent.objects.create(
            account=account,
            product=infrastructure_product,
            meter=daily_cost_meter,
            stack=stack,
            quantity=cost_decimal,
            occurred_at=timezone.now(),
            metadata={
                "source": "azure_function",
                "billing_date": today.isoformat(),
                "stack_name": stack.name
            }
        )
        
        # Create charge for billing purposes
        cost_cents = int(cost_decimal * 100)  # Convert to cents
        
        charge = Charge.objects.create(
            account=account,
            product=infrastructure_product,
            meter=daily_cost_meter,
            source=ChargeSource.USAGE,
            usage_date=today,
            description=f"Infrastructure cost for {stack.name} on {today}",
            quantity=Decimal('1'),  # One daily charge
            unit_name="day",
            unit_price_cents=cost_cents,
            amount_cents=cost_cents,
            currency=Currency.USD,
            invoiced=False
        )
        
        print(f"Created billing records for stack {stack_id}: ${cost_decimal}")
        return usage_event.id, charge.id
        
    except Stack.DoesNotExist:
        print(f"Warning: Stack {stack_id} not found, skipping")
        return None, None
    except (ValueError, TypeError) as e:
        print(f"Warning: Invalid cost value '{cost_str}' for stack {stack_id}: {e}")
        return None, None
    except Exception as e:
        print(f"Error processing stack {stack_id}: {e}")
        return None, None


def receive_billing_info(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            data = json.loads(request.body).get("data", {})
            print("Received billing info:", data)
            
            # Validate input format: {"<stack_id>": "cost"}
            if not isinstance(data, dict):
                return JsonResponse({"error": "Invalid data format. Expected dictionary."}, status=400)
            
            # Get or create infrastructure product and meter
            infrastructure_product, _ = Product.objects.get_or_create(
                code="infrastructure",
                defaults={
                    "name": "Infrastructure Costs",
                    "taxable": True
                }
            )
            
            daily_cost_meter, _ = Meter.objects.get_or_create(
                code="daily_cost",
                defaults={
                    "description": "Daily infrastructure cost in USD",
                    "unit_name": "USD"
                }
            )
            
            created_events = []
            created_charges = []
            today = timezone.localdate()
            
            for stack_id, cost_str in data.items():
                usage_event_id, charge_id = _process_stack_billing(
                    stack_id, cost_str, infrastructure_product, daily_cost_meter, today
                )
                if usage_event_id and charge_id:
                    created_events.append(usage_event_id)
                    created_charges.append(charge_id)
            
            return JsonResponse({
                "message": "Billing info received and processed successfully.",
                "created_events": len(created_events),
                "created_charges": len(created_charges),
                "usage_events": created_events,
                "charges": created_charges
            }, status=200)
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except Exception as e:
            print(f"Unexpected error processing billing info: {e}")
            return JsonResponse({"error": "An error occurred while processing billing info."}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)