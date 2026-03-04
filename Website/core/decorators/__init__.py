from functools import wraps
from typing import Any, Callable, Union
import logging

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED

from django.http import HttpRequest
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect

logger = logging.getLogger(__name__)


class AuthHttpRequest(HttpRequest):
    pass


def oauth_required():
    """
    Decorator to authenticate requests via WorkOS-backed Django sessions.

    WorkOS AuthKit handles the login flow and establishes Django sessions
    (via ``django.contrib.auth.login``).  This decorator simply verifies
    that the current request has an authenticated session and sets
    ``request.auth_user`` for backward compatibility with existing views.
    """

    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(view_func)
        def _wrapped_view(*args: Any, **kwargs: Any):
            request = args[1] if len(args) > 1 else args[0]

            if not isinstance(request, (WSGIRequest, Request)):
                raise ValueError("Request is not a WSGIRequest or DRF Request")

            is_api_call = request.path.startswith("/api/")

            # Django session authentication (established by WorkOS AuthKit login)
            user = getattr(request, "user", None)

            if user is not None and user.is_authenticated:
                setattr(request, "auth_user", user)
                logger.debug(
                    f"Authenticated request for user: {user.username} on {request.path}"
                )
                return view_func(*args, **kwargs)

            logger.warning(f"Unauthenticated request to {request.path}")
            return _unauthorized_response(is_api_call, "Authentication required.", request)

        return _wrapped_view

    return decorator


def _unauthorized_response(
    is_api_call: bool, error: str, request: Union[Request, WSGIRequest]
) -> Union[Response, HttpResponseRedirect, HttpResponsePermanentRedirect]:
    if is_api_call:
        return Response({"error": error}, status=HTTP_401_UNAUTHORIZED)
    return redirect(f"{settings.HOST}/login/?next={request.path}")
