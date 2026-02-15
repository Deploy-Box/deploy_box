import stripe

def create_stripe_customer(name: str, email: str) -> str:
    """
    Create a new customer in Stripe
    """
    customer = stripe.Customer.create(
        name=name,
        email=email
    )

    return customer.id