from django.shortcuts import redirect
from django.http import JsonResponse
from django.http import HttpRequest
from functools import wraps
from typing import Any, Callable, List
from django.conf import settings

def oauth_required(allowed_applications: List[str] | None = None):

    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to ensure that the user is authenticated via WorkOS-backed Django session."""
        
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args: tuple[Any, ...], **kwargs: dict[str, Any]):
            is_api_call = request.path.startswith('/api/')

            user = getattr(request, 'user', None)
            if user is None or not user.is_authenticated:
                error_message = "Authentication required."
                return decide_return(is_api_call, error_message, request)

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    
    return decorator

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
