# core/decorators.py
from functools import wraps
from typing import Any, Callable, List, Union

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import get_authorization_header
from rest_framework.renderers import JSONRenderer

from django.http import HttpRequest
from django.utils import timezone
from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from accounts.models import UserProfile

class AuthHttpRequest(HttpRequest):
    pass

def oauth_required(allowed_applications: Union[List[str], None] = None):
    """
    DRF-based decorator to authenticate access using OAuth2 tokens.
    Supports optional application restrictions and profile binding.
    """

    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(view_func)
        def _wrapped_view(request: Request, *args: Any, **kwargs: Any):
            is_api_call = request.path.startswith("/api/")
            access_token = request.session.get("access_token")

            if not access_token:
                auth = get_authorization_header(request).decode("utf-8")
                if auth.startswith("Bearer "):
                    access_token = auth.split(" ")[1]

            if not access_token:
                return _unauthorized_response(is_api_call, "No access token provided.", request)

            authenticator = OAuth2Authentication()

            try:
                user_auth_tuple = authenticator.authenticate(request)
                if not user_auth_tuple:
                    return _unauthorized_response(is_api_call, "Invalid or expired token.", request)

                user, token = user_auth_tuple

                if token.expires < timezone.now():
                    return _unauthorized_response(is_api_call, "Access token has expired.", request)

                if allowed_applications and token.application.name not in allowed_applications:
                    return _unauthorized_response(
                        is_api_call,
                        f"Application '{token.application.name}' is not allowed.",
                        request
                    )

                try:
                    user_profile = UserProfile.objects.get(user=user)
                except UserProfile.DoesNotExist:
                    return _unauthorized_response(is_api_call, "User profile not found.", request)

                setattr(request, "auth_user", user_profile)
                request.user = user
                request.auth = token
                print(request.user)

            except AuthenticationFailed as e:
                print("UNauthorized")
                return _unauthorized_response(is_api_call, str(e), request)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def _unauthorized_response(
    is_api_call: bool, error: str, request: Request
) -> Union[Response, HttpResponseRedirect, HttpResponsePermanentRedirect]:
    if is_api_call:
        return Response({"error": error}, status=HTTP_401_UNAUTHORIZED)
    return redirect(f"{settings.HOST}/login/?next={request.path}")
