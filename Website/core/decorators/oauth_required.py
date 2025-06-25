# core/decorators.py
from functools import wraps
from typing import Any, Callable, List, Union
import logging

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED
from rest_framework.authentication import get_authorization_header

from django.http import HttpRequest
from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone
from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect

from oauth2_provider.models import AccessToken

logger = logging.getLogger(__name__)


class AuthHttpRequest(HttpRequest):
    pass


def oauth_required(required_scope: Union[str, List[str], None] = None, allow_m2m: bool = True):
    """
    Decorator to authenticate access using OAuth2 tokens.
    Supports scope-based authorization and both user-based and M2M authentication.
    
    Args:
        required_scope: Single scope string, list of scopes, or None for no scope requirement
        allow_m2m: Whether to allow machine-to-machine authentication (tokens without users)
    """

    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(view_func)
        def _wrapped_view(*args: Any, **kwargs: Any):
            request = args[1]

            if not isinstance(request, WSGIRequest) and not isinstance(request, Request):
                print(type(request))
                raise ValueError("Request is not a WSGIRequest or Request")

            is_api_call = request.path.startswith("/api/")
            logger.info(
                f"oauth_required decorator called for path: {request.path}, is_api_call: {is_api_call}"
            )

            # Try to get access token from session first (for web requests)
            access_token = request.session.get("access_token")
            logger.info(f"Session access_token found: {access_token is not None}")

            # If no session token, try Authorization header
            if not access_token:
                auth = get_authorization_header(request).decode("utf-8")
                logger.info(
                    f"Authorization header: {auth[:50]}..."
                    if len(auth) > 50
                    else f"Authorization header: {auth}"
                )
                if auth.startswith("Bearer "):
                    access_token = auth.split(" ")[1]
                    logger.info("Bearer token extracted from header")

            if not access_token:
                logger.warning("No access token found in session or header")
                return _unauthorized_response(
                    is_api_call, "No access token provided.", request
                )

            logger.info(f"Access token found: {access_token[:20]}...")

            try:
                # Fetch the AccessToken from the database
                token = AccessToken.objects.get(token=access_token)
                logger.info(
                    f"AccessToken found in database for application: {token.application.name}"
                )

                # Check if the token is expired
                if token.expires < timezone.now():
                    logger.warning(
                        f"Token expired at {token.expires}, current time: {timezone.now()}"
                    )
                    return _unauthorized_response(
                        is_api_call, "Access token has expired.", request
                    )

                # Check scope requirements
                if required_scope:
                    token_scopes = token.scope.split() if token.scope else []
                    required_scopes = [required_scope] if isinstance(required_scope, str) else required_scope
                    
                    # Check if all required scopes are present in token
                    missing_scopes = [scope for scope in required_scopes if scope not in token_scopes]
                    if missing_scopes:
                        logger.warning(
                            f"Token missing required scopes: {missing_scopes}. "
                            f"Token has: {token_scopes}, required: {required_scopes}"
                        )
                        return _unauthorized_response(
                            is_api_call,
                            f"Access token missing required scopes: {', '.join(missing_scopes)}",
                            request,
                        )

                # Handle user-based vs M2M authentication
                if token.user:
                    # User-based authentication
                    user_profile = token.user
                    logger.info(f"UserProfile found for user: {token.user.username}")

                    setattr(request, "auth_user", user_profile)
                    request.user = token.user
                    # Only set auth attribute for DRF Request objects
                    if isinstance(request, Request):
                        request.auth = token
                    logger.info(
                        f"Request authenticated successfully for user: {token.user.username}"
                    )
                else:
                    # M2M authentication
                    if not allow_m2m:
                        logger.warning("M2M authentication not allowed for this endpoint")
                        return _unauthorized_response(
                            is_api_call, "User-based authentication required.", request
                        )
                    
                    # Set application context for M2M
                    setattr(request, "auth_application", token.application)
                    setattr(request, "auth_token", token)
                    setattr(request, "auth_user", None)
                    # Only set user to None for DRF Request objects
                    if isinstance(request, Request):
                        request.user = None
                    
                    logger.info(
                        f"M2M request authenticated successfully for application: {token.application.name}"
                    )

            except AccessToken.DoesNotExist:
                logger.error("AccessToken not found in database")
                return _unauthorized_response(
                    is_api_call, "Invalid access token.", request
                )

            return view_func(*args, **kwargs)
        
        return _wrapped_view
    
    return decorator


def _unauthorized_response(
    is_api_call: bool, error: str, request: Union[Request, WSGIRequest]
) -> Union[Response, HttpResponseRedirect, HttpResponsePermanentRedirect]:
    if is_api_call:
        return Response({"error": error}, status=HTTP_401_UNAUTHORIZED)
    return redirect(f"{settings.HOST}/login/?next={request.path}")
