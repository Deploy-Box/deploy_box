from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory, override_settings

from core.middleware import LoginRequiredMiddleware, WorkOSSessionMiddleware

UserProfile = get_user_model()


def _noop_response(request):
    """Dummy get_response callable that returns the request itself for inspection."""
    return request


class WorkOSSessionMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = WorkOSSessionMiddleware(_noop_response)
        self.user = UserProfile.objects.create_user(username="alice", password="pw")

    def _add_session(self, request):
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()

    def test_sets_user_when_session_has_valid_id(self):
        request = self.factory.get("/dashboard/")
        self._add_session(request)
        request.session[WorkOSSessionMiddleware.SESSION_KEY] = str(self.user.pk)
        self.middleware(request)
        self.assertEqual(request.user, self.user)

    def test_sets_anonymous_when_session_empty(self):
        request = self.factory.get("/dashboard/")
        self._add_session(request)
        self.middleware(request)
        self.assertIsInstance(request.user, AnonymousUser)

    def test_flushes_session_when_user_not_found(self):
        request = self.factory.get("/dashboard/")
        self._add_session(request)
        request.session[WorkOSSessionMiddleware.SESSION_KEY] = "nonexistent_pk"
        self.middleware(request)
        self.assertIsInstance(request.user, AnonymousUser)
        self.assertNotIn(WorkOSSessionMiddleware.SESSION_KEY, request.session)


class LoginRequiredMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = LoginRequiredMiddleware(_noop_response)
        self.user = UserProfile.objects.create_user(username="bob", password="pw")

    def test_allows_home_page(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        response = self.middleware(request)
        # _noop_response returns the request object, not a redirect
        self.assertEqual(response, request)

    def test_allows_public_prefix(self):
        for path in ["/login", "/signup", "/stacks", "/pricing", "/api/v1/test", "/admin/"]:
            request = self.factory.get(path)
            request.user = AnonymousUser()
            response = self.middleware(request)
            self.assertEqual(response, request, f"Path {path} should be public")

    def test_redirects_unauthenticated_on_private_path(self):
        request = self.factory.get("/dashboard/")
        request.user = AnonymousUser()
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)

    def test_allows_authenticated_on_private_path(self):
        request = self.factory.get("/dashboard/")
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response, request)

    def test_is_public_exact_home(self):
        self.assertTrue(self.middleware._is_public("/"))

    def test_is_public_nested_public_path(self):
        self.assertTrue(self.middleware._is_public("/blogs/my-post"))

    def test_is_not_public_private_path(self):
        self.assertFalse(self.middleware._is_public("/dashboard/"))
        self.assertFalse(self.middleware._is_public("/profile/settings"))
