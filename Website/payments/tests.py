from django.test import TestCase
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from organizations.models import Organization
from stacks.models import PurchasableStack
from projects.models import Project
from payments.views import create_checkout_session, check_organization_payment_methods
from core.decorators import AuthHttpRequest

User = get_user_model()

class PaymentViewsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test organization without stripe_customer_id
        self.organization = Organization.objects.create(
            name='Test Organization',
            email='org@example.com',
            stripe_customer_id=''  # Empty stripe_customer_id
        )
        
        # Create test project
        self.project = Project.objects.create(
            name='Test Project',
            organization=self.organization
        )
        
        # Create test purchasable stack
        self.purchasable_stack = PurchasableStack.objects.create(
            name='Test Stack',
            description='Test stack description',
            price_id='price_test123',
            variant='test'
        )

    @patch('payments.views.stripe')
    def test_create_checkout_session_creates_stripe_customer(self, mock_stripe):
        """Test that create_checkout_session creates a Stripe customer when organization doesn't have one."""
        
        # Mock Stripe responses
        mock_price = MagicMock()
        mock_price.unit_amount = 1000  # $10.00
        mock_stripe.Price.retrieve.return_value = mock_price
        
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_stripe.Customer.create.return_value = mock_customer
        
        mock_session = MagicMock()
        mock_session.id = 'cs_test123'
        mock_stripe.checkout.Session.create.return_value = mock_session
        
        # Create request
        request = self.factory.post('/api/v1/payments/checkout/create/test-org/')
        request.auth_user = self.user
        request.body = b'{"stack_id": "' + str(self.purchasable_stack.id).encode() + b'", "project_id": "' + str(self.project.id).encode() + b'"}'
        
        # Mock get_organization to return our test organization
        with patch('payments.views.get_organization', return_value=self.organization):
            response = create_checkout_session(request, str(self.organization.id))
        
        # Verify Stripe customer was created
        mock_stripe.Customer.create.assert_called_once_with(
            email=self.organization.email,
            name=self.organization.name,
            metadata={'organization_id': str(self.organization.id)}
        )
        
        # Verify organization was updated with new stripe_customer_id
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.stripe_customer_id, 'cus_test123')
        
        # Verify checkout session was created
        mock_stripe.checkout.Session.create.assert_called_once()
        
        # Verify response
        self.assertEqual(response.status_code, 200)

    @patch('payments.views.stripe')
    def test_check_organization_payment_methods_creates_stripe_customer(self, mock_stripe):
        """Test that check_organization_payment_methods creates a Stripe customer when organization doesn't have one."""
        
        # Mock Stripe customer creation
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_stripe.Customer.create.return_value = mock_customer
        
        # Mock payment methods list (empty)
        mock_payment_methods = MagicMock()
        mock_payment_methods.data = []
        mock_stripe.PaymentMethod.list.return_value = mock_payment_methods
        
        # Test the function
        has_payment_methods, error_message = check_organization_payment_methods(self.organization)
        
        # Verify Stripe customer was created
        mock_stripe.Customer.create.assert_called_once_with(
            email=self.organization.email,
            name=self.organization.name,
            metadata={'organization_id': str(self.organization.id)}
        )
        
        # Verify organization was updated
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.stripe_customer_id, 'cus_test123')
        
        # Verify return values
        self.assertFalse(has_payment_methods)
        self.assertIn("No payment methods found", error_message)
