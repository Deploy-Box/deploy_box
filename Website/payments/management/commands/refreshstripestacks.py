from django.core.management.base import BaseCommand
from django.conf import settings
from oauth2_provider.models import Application
from stacks.models import PurchasableStack
from django.contrib.auth import get_user_model
import stripe

User = get_user_model()


class Command(BaseCommand):
    help = 'Create an OAuth2 application for machine-to-machine authentication'

    def handle(self, *args, **options):
        try:
            stripe.api_key = settings.STRIPE.get("SECRET_KEY")

            # List active products (optional filters can be used)
            products = stripe.Product.list(active=True)

            print("Found ", len(products), " products")

            purchasable_stacks = []

            # Print product names and IDs
            for product in products.auto_paging_iter():
                if product.metadata.get("is_stack") == "true":
                    purchasable_stacks.append(product)

            print("Found ", len(purchasable_stacks), " purchasable stacks")

            # Upsert purchasable stacks based on price_id
            for stack in purchasable_stacks:
                # Extract type, variant, and version from metadata or name
                metadata = stack.metadata
                stack_type = metadata.get("type", "unknown")
                variant = metadata.get("variant", "default")
                version = metadata.get("version", "1.0")
                
                # Get the price ID from the default price
                price_id = stack.default_price if stack.default_price else ""
                
                PurchasableStack.objects.update_or_create(
                    price_id=price_id,  # lookup field
                    defaults={          # fields to update/create
                        'type': stack_type,
                        'variant': variant,
                        'version': version,
                        'name': stack.name,
                        'description': stack.description or "check out this stack",
                    }
                )

                print(f"Upserted stack: {stack.name}")


        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create OAuth application: {str(e)}')
            ) 