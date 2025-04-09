import json
import time
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.contrib.auth.models import User

from core.decorators import oauth_required
from api.services.stack_services import deploy_stack
from api.models import AvailableStack, Stack, StackDatabase
from accounts.models import UserProfile, Project


stripe.api_key = settings.STRIPE.get("SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)


@csrf_exempt
def stripe_config(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        # Handle non-GET requests
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    stripe_config = {"publicKey": STRIPE_PUBLISHABLE_KEY}
    return JsonResponse(stripe_config, safe=False)


def create_stripe_user(user: User):
    # Create a new customer in Stripe
    try:
        customer = stripe.Customer.create(
            name=f"{user.first_name} {user.last_name}",
            email=user.email,
        )

        return customer.id

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@oauth_required
def create_intent(request: HttpRequest) -> JsonResponse:
    try:
        user_profile = UserProfile.objects.get(user=request.user)

        intent = stripe.SetupIntent.create(
            customer=user_profile.stripe_customer_id,
        )
        print(intent.client_secret)
        return JsonResponse({"client_secret": intent.client_secret})
    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@oauth_required
def save_payment_method(request: HttpRequest) -> JsonResponse:
    try:
        payment_method_id = request.POST.get("payment_method")

        user_profile = UserProfile.objects.get(user=request.user)
        customer_id = user_profile.stripe_customer_id

        # Attach the payment method to the customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id,  # Use the current logged-in user's Stripe customer ID
        )

        # Optionally, you can set this payment method as the default for subscriptions
        stripe.customers.update(
            customer_id,  # Use the current logged-in user's Stripe customer ID
            invoice_settings={"default_payment_method": payment_method_id},
        )

        return JsonResponse({"status": "Payment method saved successfully"})

    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def create_checkout_session(request: HttpRequest) -> JsonResponse:
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
        price_id = AvailableStack.objects.get(id=stack_id).price_id
        checkout_session = stripe.checkout.Session.create(
            customer=UserProfile.objects.get(
                user_id=request.user.id
            ).stripe_customer_id,
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


@csrf_exempt
def create_subscription(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        data = json.loads(request.body)
        customer_id = data.get("customer_id")  # The customer ID created earlier
        price_id = "price_1R1GKgC8awKXIVJaWsiksB7O"  # The ID for the metered plan

        print(data)

        try:
            # Create the subscription for the customer
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[
                    {
                        "price": price_id,
                    }
                ],
                expand=["latest_invoice.payment_intent"],
            )

            return JsonResponse(
                {
                    "subscription_id": subscription.id,
                    "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                }
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=400)


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


@csrf_exempt
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    # Use `stripe listen --forward-to http://127.0.0.1:8000/api/payments/webhook` to listen for events
    WEBHOOK_SECRET = settings.STRIPE.get("WEBHOOK_SECRET", None)
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    # 

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
        print("Payment was successful.")

        session = event["data"]["object"]

        # Get Stripe Customer ID
        stripe_customer_id = session.get("customer")

        # Fetch the user based on the Stripe Customer ID
        try:
            user_account = UserProfile.objects.get(
                stripe_customer_id=stripe_customer_id
            )
            user = User.objects.get(id=user_account.user_id)
        except User.DoesNotExist:
            print(f"User with Stripe ID {stripe_customer_id} not found.")
            return HttpResponse("Customer does not exist", status=400)

        # Retrieve line items to get the Price ID
        line_items = stripe.checkout.Session.list_line_items(session["id"])
        if not line_items["data"]:
            print("No line items found in session.")
            return HttpResponse("No line items", status=400)

        price_id = line_items["data"][0]["price"]["id"]  # Get first price ID

        # Fetch the corresponding stack based on Price ID
        try:
            available_stack = AvailableStack.objects.get(price_id=price_id)
        except AvailableStack.DoesNotExist:
            print(f"Stack with Price ID {price_id} not found.")
            return HttpResponse(status=400)
        
        # Get the project ID
        project_id = 1

        # TODO: Get the project ID from the user
        project = Project.objects.get(id=project_id)

        # Create a stack entry for the user
        stack = Stack.objects.create(name="MERN Stack", purchased_stack=available_stack, project=project)

        # TODO: Deploy the stack
        # request.user = user
        # deploy_stack(request, stack.id)

        return HttpResponse(status=200)

    return HttpResponse(status=200)


# new branch work################################################################################################


@csrf_exempt
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


@csrf_exempt
def get_customer_id(request):
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            user_id = data.get("user_id")  # Extract user_id from the JSON payload

            # Check if user_id is provided
            if not user_id:
                return JsonResponse({"error": "user_id is required"}, status=400)

            # Query the UserProfile by the provided user_id
            try:
                user = UserProfile.objects.get(user_id=user_id)
                customer_id = (
                    user.stripe_customer_id
                )  # Assuming customer_id is a field in UserProfile

                return JsonResponse({"customer_id": customer_id}, status=200)

            except UserProfile.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)


@csrf_exempt
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
