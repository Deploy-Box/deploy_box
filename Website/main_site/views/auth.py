from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View


class AuthView(View):
    """Class-based view for all authentication-related functionality.
    All auth flows go through WorkOS AuthKit."""

    def login(self, request: HttpRequest) -> HttpResponse:
        """Redirect to WorkOS AuthKit for login."""
        next_url = request.GET.get('next', '')
        workos_url = '/api/v1/accounts/oauth/workos/'
        if next_url:
            workos_url += f'?state={next_url}'
        return redirect(workos_url)

    def signup(self, request: HttpRequest) -> HttpResponse:
        """Redirect to WorkOS AuthKit for signup."""
        return redirect('/api/v1/accounts/oauth/workos/')


auth_view = AuthView()
