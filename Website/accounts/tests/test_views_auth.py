from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock
from rest_framework.test import APIRequestFactory
from ..views import OAuthPasswordLoginView, LogoutAPIView, OAuthClientCredentialsView

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

    @override_settings(
        OAUTH2_PASSWORD_CREDENTIALS={
            "token_url": "https://example.test/token",
            "client_id": "cid",
            "client_secret": "csecret",
        }
    )
    @patch("accounts.views.requests.post")
    @patch("accounts.views.authenticate")
    def test_oauth_password_login_success(self, mock_auth, mock_post):
        mock_auth.return_value = self.user

        fake_resp = Mock(status_code=200)
        fake_resp.json.return_value = {"access_token": "A", "refresh_token": "R"}
        mock_post.return_value = fake_resp

        url = reverse("accounts:api-login")
        drf_request = self.factory.post(
            url,
            {"username": "kaleb", "password": "test123"},
            format="json"
        )

        attach_session(drf_request)

        resp = OAuthPasswordLoginView.as_view()(drf_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.data.keys()) & {"access_token", "refresh_token"}, {"access_token", "refresh_token"})

    @patch("accounts.views.authenticate", return_value=None)
    def test_oauth_password_login_invalid_credentials(self, mock_auth):
        url = reverse("accounts:api-login")
        drf_request = self.factory.post(url, {"username": "jacob", "password": "bad"}, format="json")
        attach_session(drf_request)
        resp = OAuthPasswordLoginView.as_view()(drf_request)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data, {"detail": "Invalid credentials"})

    def test_logout_ok(self):
        url = reverse("accounts:api-logout")
        drf_request = self.factory.post(url)
        attach_session(drf_request)
        resp = LogoutAPIView.as_view()(drf_request)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Logged out successfully", resp.data.get("detail", ""))