from django.shortcuts import redirect
from django.contrib.auth.models import AnonymousUser


class WorkOSSessionMiddleware:
    """
    Replaces Django's AuthenticationMiddleware.

    Reads the authenticated user's PK from the session (written during the
    WorkOS OAuth callback) and attaches the UserProfile to ``request.user``.
    Falls back to AnonymousUser when no valid session exists.
    """

    SESSION_KEY = "_workos_user_id"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get(self.SESSION_KEY)
        if user_id:
            from accounts.models import UserProfile

            try:
                request.user = UserProfile.objects.get(pk=user_id)
            except UserProfile.DoesNotExist:
                request.session.flush()
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()
        return self.get_response(request)


class LoginRequiredMiddleware:
    """
    Middleware that redirects unauthenticated users to the login page
    for any path that isn't explicitly public.
    """

    # URL prefixes that do NOT require authentication.
    PUBLIC_PREFIXES = (
        "/",             # exact home page (handled by exact match below)
        "/login",
        "/signup",
        "/stacks",
        "/pricing",
        "/contact",
        "/still-configuring",
        "/subdomain-not-found",
        "/docs",
        "/marketplace",
        "/stacks-marketplace",
        "/components",
        "/examples",
        "/blogs",
        "/admin",
        "/api",
        "/ckeditor5",
        "/static",
        "/media",
        "/favicon.ico",
        "/google0f33857d0e9df9a5.html",
        "/sitemap.xml",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not self._is_public(request.path):
            return redirect("main_site:login")
        return self.get_response(request)

    def _is_public(self, path: str) -> bool:
        """Return True if the path is publicly accessible."""
        # Exact home page
        if path == "/":
            return True
        # Check all public prefixes
        for prefix in self.PUBLIC_PREFIXES:
            if prefix != "/" and path.startswith(prefix):
                return True
        return False