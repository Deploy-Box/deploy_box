from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
import time 
from oauth2_provider.models import AccessToken
from django.core.exceptions import ObjectDoesNotExist

def oauth_required(view_func):
    """Decorator to ensure that the user is authenticated and has a valid access token."""
    
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if the request is for an API call (by checking the 'Accept' header)
        is_api_call = request.path.startswith("/api/")  # Check if it's an API endpoint

        # Get the access token from the Authorization header
        access_token = request.headers.get("Authorization", "").split(" ")[-1]

        if not access_token:
            # If no access token in the header, try to get it from the session
            access_token = get_access_token_from_session(request)

        print(f"Access Token: {access_token}")

        if not access_token:
            return decide_return(is_api_call, "Unauthorized: No access token provided", request)
            

        expires_at = get_access_token_details(access_token)

        if not expires_at:
            # If we couldn't find the access token in the database, return unauthorized
            return decide_return(is_api_call, "Unauthorized: Invalid access token", request)
        
        # Check if the access token is expired
        if not check_access_token(expires_at):
            return decide_return(is_api_call, "Unauthorized: Token expired", request)

        if not access_token:
            decide_return(is_api_call, "Unauthorized: Access token expired or invalid", request)

        # If the access token is valid, continue with the view
        return view_func(request, *args, **kwargs)

    return _wrapped_view

def decide_return(is_api_call: bool, error: str, request):
    """
    Helper function to decide the return type based on whether it's an API call or not.
    """
    if is_api_call:
        # Return a JSON response for API calls
        return JsonResponse({"error": error}, status=401)
    else:
        # Redirect to login for non-API calls
        return redirect(f"{settings.HOST}/accounts/login/?next={request.path}")


def get_access_token_from_session(request):
    """
    Retrieve the access token from the session.
    This function attempts to get the access token from the session.
    This is useful for cases where the access token is stored in the session after login.
    """
  
    return request.session.get("access_token")

def get_access_token_details(access_token):
    """
    Retrieve access token details from the database.
    This function returns the access token, refresh token, and expiration time.
    """
    try:
        access_token_obj = AccessToken.objects.get(token=access_token)
        print(f"Access Token Object: {access_token_obj}")  # Debug statement to check the access token object
        expires_at = access_token_obj.expires.timestamp()  # Convert to timestamp
        return expires_at
    except ObjectDoesNotExist:
        return None  # Access token not found

   
def check_access_token(expires_at):
    """
    Check if the access token is valid. If expired, refresh it using the refresh token.
    Returns a tuple of (access_token, refresh_token, expires_at).
    """
    # Check if the access token is expired
    if time.time() > expires_at:
        return False

    return True
    