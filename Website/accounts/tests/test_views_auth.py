from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock
from rest_framework.test import APIRequestFactory
from ..views import LogoutAPIView, OAuthClientCredentialsView

UserProfile = get_user_model()

def attach_session(django_request):
    from django.contrib.sessions.middleware import SessionMiddleware
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(django_request)
    django_request.session.save()

class TestAuthViews(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = UserProfile.objects.create_user(username="kaleb", password="test123")

    def test_logout_ok(self):
        url = reverse("accounts:api-logout")
        drf_request = self.factory.post(url)
        attach_session(drf_request)
        resp = LogoutAPIView.as_view()(drf_request)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Logged out successfully", resp.data.get("detail", ""))