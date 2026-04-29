from datetime import date

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from organizations.models import Organization
from stacks.models import PurchasableStack
from projects.models import Project
from payments.models import Invoice
from payments.views import create_checkout_session, check_organization_payment_methods

User = get_user_model()


class PaymentViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.organization = Organization.objects.create(
            name='Test Organization',
            email='org@example.com',
            stripe_customer_id=''
        )
        self.project = Project.objects.create(
            name='Test Project',
            organization=self.organization
        )
        self.purchasable_stack = PurchasableStack.objects.create(
            name='Test Stack',
            description='Test stack description',
            price_id='price_test123',
            variant='test'
        )

    @patch('payments.views.stripe')
    def test_create_checkout_session_creates_stripe_customer(self, mock_stripe):
        mock_price = MagicMock(); mock_price.unit_amount = 1000
        mock_stripe.Price.retrieve.return_value = mock_price
        mock_customer = MagicMock(); mock_customer.id = 'cus_test123'
        mock_stripe.Customer.create.return_value = mock_customer
        mock_session = MagicMock(); mock_session.id = 'cs_test123'
        mock_stripe.checkout.Session.create.return_value = mock_session

        from django.test import RequestFactory
        factory = RequestFactory()
        payload = {
            "stack_id": str(self.purchasable_stack.id),
            "project_id": str(self.project.id),
        }
        request = factory.post(
            f"/api/v1/payments/checkout/create/{self.organization.id}/",
            data=payload,
            content_type='application/json',
        )
        request.user = self.user

        with patch('payments.views.get_organization', return_value=self.organization):
            resp = create_checkout_session(request, str(self.organization.id))

        self.assertEqual(resp.status_code, 200)
        mock_stripe.Customer.create.assert_called_once_with(
            email=self.organization.email,
            name=self.organization.name,
            metadata={'organization_id': str(self.organization.id)}
        )
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.stripe_customer_id, 'cus_test123')
        mock_stripe.checkout.Session.create.assert_called_once()

    @patch('payments.services.stripe')
    def test_check_organization_payment_methods_creates_stripe_customer(self, mock_stripe):
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_stripe.Customer.create.return_value = mock_customer
        mock_payment_methods = MagicMock()
        mock_payment_methods.data = []
        mock_stripe.PaymentMethod.list.return_value = mock_payment_methods

        has_payment_methods, error_message = check_organization_payment_methods(self.organization)

        mock_stripe.Customer.create.assert_called_once_with(
            email=self.organization.email,
            name=self.organization.name,
            metadata={'organization_id': str(self.organization.id)},
            idempotency_key=f"ensure-customer-{self.organization.id}",
        )
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.stripe_customer_id, 'cus_test123')
        self.assertFalse(has_payment_methods)
        self.assertIn("No payment methods found", error_message)


class WebhookCSRFTestCase(TestCase):
    @patch('payments.views.stripe')
    def test_webhook_csrf_exempt(self, mock_stripe):
        """POST to webhook without CSRF token should not 403."""
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {}}}
        }
        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=b'{}',
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertNotEqual(response.status_code, 403)


class WebhookEventHandlersTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Test Org", email="o@t.com", stripe_customer_id="cus_test"
        )

    @patch('payments.views.stripe')
    def test_invoice_paid_updates_status(self, mock_stripe):
        """invoice.paid event should set Invoice status to 'paid'."""
        invoice = Invoice.objects.create(
            organization=self.org, invoice_month=date(2025, 3, 1),
            status="open", subtotal_amount=100, tax_amount=0, total_amount=100,
            stripe_invoice_id="in_test123",
        )
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "invoice.paid",
            "data": {"object": {"id": "in_test123"}},
        }
        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "paid")

    @patch('payments.views.stripe')
    def test_invoice_payment_failed_keeps_open(self, mock_stripe):
        """invoice.payment_failed should keep Invoice status as 'open'."""
        invoice = Invoice.objects.create(
            organization=self.org, invoice_month=date(2025, 3, 1),
            status="draft", subtotal_amount=50, tax_amount=0, total_amount=50,
            stripe_invoice_id="in_fail456",
        )
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "invoice.payment_failed",
            "data": {"object": {"id": "in_fail456", "customer": "cus_test"}},
        }
        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "open")

    @patch('payments.views.stripe')
    def test_payment_method_detached_returns_200(self, mock_stripe):
        """payment_method.detached event should return 200."""
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "payment_method.detached",
            "data": {"object": {"id": "pm_detach123"}},
        }
        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertEqual(response.status_code, 200)

    @patch('payments.views.stripe')
    def test_unknown_event_returns_200(self, mock_stripe):
        """Unknown event types should still return 200."""
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "some.unknown.event",
            "data": {"object": {}},
        }
        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertEqual(response.status_code, 200)


class DeletePaymentMethodTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2', email='test2@example.com', password='pass123'
        )
        self.org = Organization.objects.create(
            name='Test Org', email='org@test.com', stripe_customer_id='cus_del_test'
        )

    @patch('payments.views.get_organization')
    @patch('payments.views.stripe')
    def test_deletes_requested_card_not_default(self, mock_stripe, mock_get_org):
        """Should detach the requested card, not the default card."""
        mock_get_org.return_value = self.org

        pm1 = MagicMock(); pm1.id = 'pm_default'; pm1.card = MagicMock()
        pm2 = MagicMock(); pm2.id = 'pm_to_delete'; pm2.card = MagicMock()
        mock_stripe.PaymentMethod.list.return_value = MagicMock(data=[pm1, pm2])
        mock_stripe.PaymentMethod.retrieve.return_value = pm2

        customer_mock = MagicMock()
        customer_mock.invoice_settings.default_payment_method = 'pm_default'
        mock_stripe.Customer.retrieve.return_value = customer_mock

        factory = RequestFactory()
        request = factory.delete(
            '/api/v1/payments/payment-method/delete/'
            '?organization_id={}&payment_method_id=pm_to_delete'.format(self.org.id)
        )
        request.user = self.user

        from payments.views import delete_payment_method
        response = delete_payment_method(request)
        self.assertEqual(response.status_code, 200)

        mock_stripe.PaymentMethod.detach.assert_called_once_with('pm_to_delete')
        mock_stripe.Customer.modify.assert_not_called()

    @patch('payments.views.get_organization')
    @patch('payments.views.stripe')
    def test_deleting_default_card_promotes_next(self, mock_stripe, mock_get_org):
        """Deleting the default card should promote the next available card."""
        mock_get_org.return_value = self.org

        pm1 = MagicMock(); pm1.id = 'pm_default'
        pm2 = MagicMock(); pm2.id = 'pm_other'
        mock_stripe.PaymentMethod.list.return_value = MagicMock(data=[pm1, pm2])
        mock_stripe.PaymentMethod.retrieve.return_value = pm1

        customer_mock = MagicMock()
        customer_mock.invoice_settings.default_payment_method = 'pm_default'
        mock_stripe.Customer.retrieve.return_value = customer_mock

        factory = RequestFactory()
        request = factory.delete(
            '/api/v1/payments/payment-method/delete/'
            '?organization_id={}&payment_method_id=pm_default'.format(self.org.id)
        )
        request.user = self.user

        from payments.views import delete_payment_method
        response = delete_payment_method(request)
        self.assertEqual(response.status_code, 200)

        mock_stripe.PaymentMethod.detach.assert_called_once_with('pm_default')
        mock_stripe.Customer.modify.assert_called_once_with(
            'cus_del_test',
            invoice_settings={"default_payment_method": "pm_other"},
        )


class UpdateBillingHistoryEndpointTestCase(TestCase):
    @patch('payments.views.payment_services')
    def test_post_triggers_invoice_generation(self, mock_services):
        """POST to update_billing_history should call generate_monthly_invoices."""
        mock_services.generate_monthly_invoices.return_value = [{"status": "success"}]
        response = self.client.post("/api/v1/payments/update_billing_history/")
        self.assertEqual(response.status_code, 200)
        mock_services.generate_monthly_invoices.assert_called_once()

    def test_get_returns_405(self):
        """GET to update_billing_history should return 405."""
        response = self.client.get("/api/v1/payments/update_billing_history/")
        self.assertEqual(response.status_code, 405)
