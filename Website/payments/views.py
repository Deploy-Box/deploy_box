import json
import time
import stripe
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404

from core.decorators import oauth_required, AuthHttpRequest
import stacks.services as stack_services
from stacks.models import PurchasableStack, StackDatabase
from organizations.models import Organization, OrganizationMember
from payments.services import pricing_services
from accounts.models import UserProfile

stripe.api_key = settings.STRIPE.get("SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)


def stripe_config(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        # Handle non-GET requests
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    stripe_config = {"publicKey": STRIPE_PUBLISHABLE_KEY}
    return JsonResponse(stripe_config, safe=False)


def create_stripe_user(**kwargs):
    # Create a new customer in Stripe
    try:
        print("kwargs", kwargs)
        customer = stripe.Customer.create(
            name=kwargs.get('name'), # type: ignore
            email=kwargs.get('email'), # type: ignore
        )

        return customer.id

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

def save_stripe_payment_method(request: AuthHttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method. Only POST is allowed."}, status=405)

    try:
        data = json.loads(request.body)
        payment_method_id = data.get("payment_method_id")
        organization_id = data.get("organization_id")  # Assuming organizationId is used as customerId

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        print(f"Payment Method ID: {payment_method_id}, Customer ID: {customer_id}", "Organization ID:", organization_id)

        if not payment_method_id or not customer_id:
            return JsonResponse({"error": "Missing paymentMethodId or customerId"}, status=400)

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

        return JsonResponse({"message": "Payment method saved successfully."}, status=200)

    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)

    except Exception as e:
        return JsonResponse({"error": "An error occurred while saving the payment method."}, status=400)

@oauth_required()
def create_checkout_session(request: AuthHttpRequest, org_id: int) -> JsonResponse:
    auth_user = request.auth_user
    user_profile = request.user_profile
    organization = Organization.objects.get(id=org_id)

    if request.method != "POST":
        # Handle non-POST requests
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    domain_url = settings.HOST
    data = json.loads(request.body)
    stack_id = data.get("stackId")
    try:
        print(stack_id)
        price_id = PurchasableStack.objects.get(id=stack_id).price_id
        checkout_session = stripe.checkout.Session.create(
            metadata={
                "stack_id": stack_id,
                "user_id": auth_user.id,
                "project_id": "1",
                "name": "MERN Stack",
            },
            customer=organization.stripe_customer_id,
            success_url=domain_url
            + "/payments/success?session_id={CHECKOUT_SESSION_ID}",
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


def stripe_webhook(request: HttpRequest) -> HttpResponse | JsonResponse:
    # Use `stripe listen --forward-to http://127.0.0.1:8000/api/payments/webhook` to listen for events
    # WEBHOOK_SECRET = settings.STRIPE.get("WEBHOOK_SECRET", None)
    WEBHOOK_SECRET = (
        "whsec_cae902cfa6db0bd7ecb8d400c97120467be8afb9304229d650f0dc3f4a24aca2"
    )

    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError as e:
        # Invalid payload
        print(f"Error parsing webhook payload: {e}")
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Error verifying signature: {e}")
        return HttpResponse("Invalid signature", status=400)

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # Get Stripe Customer ID
        stripe_customer_id = session.get("customer")

        # Fetch the user based on the Stripe Customer ID
        user_account = get_object_or_404(
            UserProfile, stripe_customer_id=stripe_customer_id
        )
        user = user_account.user

        # Retrieve line items to get the Price ID
        line_items = stripe.checkout.Session.list_line_items(session["id"])

        if not line_items["data"]:
            print("No line items found in session.")
            return HttpResponse("No line items", status=400)

        price_id = line_items["data"][0]["price"]["id"]  # Get first price ID

        # Fetch the corresponding stack based on Price ID
        available_stack = get_object_or_404(PurchasableStack, price_id=price_id)

        # Get the project
        project_id = session.get("metadata", {}).get("project_id")

        # Get the name
        name = session.get("metadata", {}).get("name")

        print(user, project_id, available_stack.id, name)

        # Create a stack entry for the user
        return stack_services.add_stack(user, project_id, available_stack.id, name)

    return HttpResponse(status=200)


def create_invoice(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            # Get data from the request body (e.g., customer_id, amount, description)
            data = json.loads(request.body)
            customer_id = data["customer_id"]  # Existing Stripe customer ID
            amount = data["amount"]  # Amount to charge in cents (e.g., 5000 for $50.00)
            description = data["description"]  # Description of the charge

            # Step 1: Create an invoice item
            stripe.InvoiceItem.create(
                customer=customer_id,
                amount=amount,
                currency="usd",  # You can change the currency if needed
                description=description,
            )

            # Step 2: Create the invoice for the customer
            invoice = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=True,  # Automatically finalizes and sends the invoice
            )

            # Step 3: Finalize the invoice (send to customer)
            invoice.finalize_invoice()

            return JsonResponse({"invoice_id": invoice.id, "status": invoice.status})

        except stripe.error.StripeError as e:
            return JsonResponse({"error": str(e)}, status=400)

        except Exception as e:
            return JsonResponse(
                {"error": "An error occurred while creating the invoice."}, status=400
            )


def get_customer_id(request):
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            org_id = data.get("org_id")  # Extract user_id from the JSON payload

            # Check if user_id is provided
            if not org_id:
                return JsonResponse({"error": "user_id is required"}, status=400)

            # Query the UserProfile by the provided user_id
            try:
                org = Organization.objects.get(id=org_id)
                customer_id = (
                    org.stripe_customer_id
                )  # Assuming customer_id is a field in UserProfile

                return JsonResponse({"customer_id": customer_id}, status=200)

            except UserProfile.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)


def update_invoice_billing(request):
    if request.method == "POST":
        data = json.loads(request.body)
        stack_id = data.get("stack_id")
        cost = data.get("cost")
        updated_count = StackDatabase.objects.filter(stack_id=stack_id).update(
            current_usage=0
        )
        billing = StackDatabase.objects.filter(stack_id=stack_id).update(
            pending_billed=F("pending_billed") + cost
        )

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


@oauth_required()
def create_price_item(request: HttpRequest) -> JsonResponse:
    return pricing_services.create_price_item(request)


@oauth_required()
def update_price_item(request: HttpRequest) -> JsonResponse:
    return pricing_services.update_price_item(request)


@oauth_required()
def delete_price_item(request: HttpRequest) -> JsonResponse:
    return pricing_services.delete_price_item(request)


@oauth_required()
def get_price_item_by_name(request: HttpRequest, name: str) -> JsonResponse:
    return pricing_services.get_price_item_by_name(request, name)


def get_payment_method(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method. Only GET is allowed."}, status=405)

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse({"error": "No Stripe customer found for this organization"}, status=404)

        # Retrieve the customer's default payment method
        customer = stripe.Customer.retrieve(customer_id, expand=['invoice_settings.default_payment_method'])
        default_payment_method = customer.invoice_settings.default_payment_method

        if not default_payment_method:
            return JsonResponse({"error": "No payment method found"}, status=404)

        # Format the card information
        card_info = {
            "brand": default_payment_method.card.brand,
            "last4": default_payment_method.card.last4,
            "exp_month": default_payment_method.card.exp_month,
            "exp_year": default_payment_method.card.exp_year,
        }

        return JsonResponse(card_info, status=200)

    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "An error occurred while retrieving the payment method."}, status=400)


def delete_payment_method(request: HttpRequest) -> JsonResponse:
    if request.method != "DELETE":
        return JsonResponse({"error": "Invalid request method. Only DELETE is allowed."}, status=405)

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse({"error": "No Stripe customer found for this organization"}, status=404)

        # Get all payment methods for the customer
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type='card'
        )

        if len(payment_methods.data) <= 1:
            return JsonResponse(
                {"error": "Cannot remove the only payment method. Please add another payment method first."}, 
                status=400
            )

        # Get the default payment method
        customer = stripe.Customer.retrieve(customer_id)
        default_payment_method_id = customer.invoice_settings.default_payment_method

        if default_payment_method_id:
            # Detach the payment method
            stripe.PaymentMethod.detach(default_payment_method_id)
            
            # Set the next available payment method as default
            if payment_methods.data:
                next_payment_method = next(
                    (pm for pm in payment_methods.data if pm.id != default_payment_method_id),
                    None
                )
                if next_payment_method:
                    stripe.Customer.modify(
                        customer_id,
                        invoice_settings={"default_payment_method": next_payment_method.id}
                    )

            return JsonResponse({"message": "Payment method removed successfully."}, status=200)
        else:
            return JsonResponse({"error": "No default payment method found"}, status=404)

    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "An error occurred while removing the payment method."}, status=400)
