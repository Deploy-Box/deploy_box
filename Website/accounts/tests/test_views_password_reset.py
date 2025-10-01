from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.test import APITestCase
from django.test import override_settings
from django.core import mail
from django.contrib.auth import get_user_model

User = get_user_model()

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   DEFAULT_FROM_EMAIL="noreply@test.local")
class TestPasswordResetFlow(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sam", email="sam@example.com", password="pw123")

    def test_request_and_confirm(self):
        # request
        url = reverse("accounts:api-password-reset")
        resp = self.client.post(url, {"email": "sam@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(mail.outbox), 1)

        # confirm
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse("accounts:api-password-reset-confirm", kwargs={"uidb64": uidb64, "token": token})
        resp2 = self.client.post(confirm_url, {"new_password1": "NewStrongP@ss1", "new_password2": "NewStrongP@ss1"}, format="json")
        self.assertEqual(resp2.status_code, 200)
