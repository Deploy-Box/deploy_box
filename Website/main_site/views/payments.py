import logging

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from typing import cast

from accounts.models import UserProfile
from organizations.models import Organization
from organizations.services import get_organizations
from stacks.models import PurchasableStack

logger = logging.getLogger(__name__)


class PaymentView(View):
    """Class-based view for all payment-related functionality."""

    STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)

    def home_page_view(self, request: HttpRequest, variant: str) -> HttpResponse:
        """Payment home page view - redirects to new stacks marketplace."""
        # Redirect to the new stacks marketplace with the variant as a query parameter
        return redirect(f'/stacks-marketplace/?variant={variant}')

    def _generate_stack_features(self, stack_type: str, variant: str) -> list:
        """Generate features list based on stack type and variant."""
        base_features = {
            'MERN': [
                'MongoDB Database',
                'Express.js Backend API',
                'React Frontend',
                'Node.js Runtime',
                'Docker Containerization',
                'Auto-deployment'
            ],
            'DJANGO': [
                'Django Backend',
                'PostgreSQL Database',
                'React Frontend',
                'Docker Containerization',
                'Admin Interface',
                'Auto-deployment'
            ],
            'MEAN': [
                'MongoDB Database',
                'Express.js Backend API',
                'Angular Frontend',
                'Node.js Runtime',
                'Docker Containerization',
                'Auto-deployment'
            ],
            'LAMP': [
                'Apache Web Server',
                'MySQL Database',
                'PHP Backend',
                'Docker Containerization',
                'Basic Security',
                'Auto-deployment'
            ]
        }
        
        premium_features = {
            'MERN': [
                'Everything in Basic',
                'Redis Caching',
                'Advanced Security',
                'Performance Monitoring',
                'CI/CD Pipeline',
                'Priority Support'
            ],
            'DJANGO': [
                'Everything in Basic',
                'Redis Caching',
                'Celery Task Queue',
                'Advanced Security',
                'Performance Monitoring',
                'Priority Support'
            ],
            'MEAN': [
                'Everything in Basic',
                'Redis Caching',
                'Advanced Security',
                'Performance Monitoring',
                'CI/CD Pipeline',
                'Priority Support'
            ],
            'LAMP': [
                'Everything in Basic',
                'Redis Caching',
                'Advanced Security',
                'Performance Monitoring',
                'SSL Certificate',
                'Priority Support'
            ]
        }
        
        pro_features = {
            'MERN': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ],
            'DJANGO': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ],
            'MEAN': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ],
            'LAMP': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ]
        }
        
        if variant.upper() == 'BASIC' or variant.upper() == 'FREE':
            return base_features.get(stack_type, ['Basic features'])
        elif variant.upper() == 'PREMIUM':
            return premium_features.get(stack_type, ['Premium features'])
        elif variant.upper() == 'PRO':
            return pro_features.get(stack_type, ['Pro features'])
        else:
            return base_features.get(stack_type, ['Basic features'])

    def stacks_marketplace_view(self, request: HttpRequest) -> HttpResponse:
        """Stacks marketplace view with filter options."""
        is_authenticated = request.user.is_authenticated

        if is_authenticated:
            user_profile = cast(UserProfile, request.user)
            organizations = get_organizations(user_profile)

            # Look through orgs until we find one with projects
            organization = None
            projects = []
            project = None
            for org in organizations:
                org_projects = org.get_projects()
                print(org_projects)
                if org_projects:
                    organization = org
                    projects = org_projects
                    project = projects[0]
                    break

        else:
            organization = None
            project = None

        print(organization)
        print(project)
        
        # Get variant from query parameter, default to 'BASIC'
        variant = request.GET.get('variant', 'BASIC').upper()
        
        # Get stacks with pricing information (same as stack marketplace)
        stripe.api_key = settings.STRIPE.get("SECRET_KEY")
        
        stack_options = []
        db_stacks = PurchasableStack.objects.all()  # Get all stacks, filter in template
        print("here is stacks: ", db_stacks)
        
        for stack in db_stacks:
            try:
                # Map stack type to icon and color
                icon_map = {
                    'MERN': '⚛️',
                    'DJANGO': '🐍',
                    'MEAN': '🅰️',
                    'LAMP': '🐘'
                }
                
                color_map = {
                    'BASIC': 'emerald',
                    'PREMIUM': 'amber',
                    'PRO': 'purple',
                    'FREE': 'emerald'
                }
   
                stack_options.append({
                    'id': str(stack.id),
                    'name': stack.name,
                    'type': stack.type,
                    'variant': stack.variant,
                    'description': stack.description,
                    'features': stack.features,
                    'icon': icon_map.get(stack.type, '📦'),
                    'color': color_map.get(stack.variant, 'emerald'),
                    'popular': False,
                    'is_from_database': True
                })
            except stripe.error.StripeError as e: # type: ignore[attr-defined]
                # Log error but continue with other stacks
                logger.error(f"Error fetching price for stack {stack.id}: {e}")
                continue
        
        return render(
            request,
            "payments/stacks_marketplace.html",
            {
                "organization_id": organization.id if organization else None,
                "project_id": project.id if project else None,
                "stack_options": stack_options,
                "selected_variant": variant,
            },
        )

    def add_card_view(self, request: HttpRequest) -> HttpResponse:
        """Add card view."""
        return render(
            request,
            "payments/add-card.html",
            {"stripe_publishable_key": self.STRIPE_PUBLISHABLE_KEY},
        )

    def success_view(self, request: HttpRequest) -> HttpResponse:
        """Payment success view."""
        return render(request, "payments/success.html")

    def cancelled_view(self, request: HttpRequest) -> HttpResponse:
        """Payment cancelled view."""
        return render(request, "payments/cancelled.html")


payment_view = PaymentView()
