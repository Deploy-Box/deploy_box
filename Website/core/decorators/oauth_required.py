from oauth2_provider.models import AccessToken  # type: ignore
from functools import wraps
from typing import Any, Callable, List
from django.http import HttpRequest, JsonResponse  # type: ignore
from django.shortcuts import redirect  # type: ignore
from django.utils import timezone  # type: ignore
from django.conf import settings  # type: ignore
from django.contrib.auth.models import User  # type: ignore


def oauth_required(allowed_applications: List[str] | None = None):

    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to ensure that the user is authenticated and has a valid access token."""

        @wraps(view_func)
        def _wrapped_view(
            request: HttpRequest, *args: tuple[Any, ...], **kwargs: dict[str, Any]
        ):
            # Determine if the request is an API call
            is_api_call = request.path.startswith("/api/")
            access_token = request.session.get("access_token")

            if not access_token:
                # Retrieve the access token from the Authorization header
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    access_token = auth_header.split(" ")[1]
                else:
                    access_token = None

            if not access_token:
                # If no access token is provided, return an error
                error_message = "No access token provided."
                return decide_return(is_api_call, error_message, request)

            try:
                # Fetch the AccessToken from the database
                token = AccessToken.objects.get(token=access_token)

                # Check if the token is expired
                if token.expires < timezone.now():
                    error_message = "Access token has expired."
                    return decide_return(is_api_call, error_message, request)

            except AccessToken.DoesNotExist:
                error_message = "Invalid access token."
                return decide_return(is_api_call, error_message, request)

            # Check if the token's application is in the allowed applications
            if allowed_applications:
                if token.application.name not in allowed_applications:
                    error_message = (
                        f"Application '{token.application.name}' is not allowed."
                    )
                    return JsonResponse(
                        {
                            "error": f"Application '{token.application.name}' is not allowed."
                        },
                        status=401,
                    )

            auth_request = AuthHttpRequest(token.user, request)

            # If the token is valid, continue with the view
            return view_func(auth_request, *args, **kwargs)

        return _wrapped_view

    return decorator


class AuthHttpRequest(HttpRequest):
    auth_user: User

    def __init__(self, auth_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_user = auth_user


def decide_return(is_api_call: bool, error: str, request: HttpRequest) -> Any:
    """
    Helper function to decide the return type based on whether it's an API call or not.
    """
    if is_api_call:
        # Return a JSON response for API calls
        return JsonResponse({"error": error}, status=401)
    else:
        # Redirect to login for non-API calls
        return redirect(f"{settings.HOST}/login/?next={request.path}")
