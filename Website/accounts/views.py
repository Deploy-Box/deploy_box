from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from .models import UserProfile
from django.conf import settings
from django.http import JsonResponse
from requests import post
import os
import base64
import hashlib
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import time
from .decorators.oauth_required import oauth_required
from payments.views import create_stripe_user
import logging

logger = logging.getLogger(__name__)


@oauth_required
def protected_view(request):
    return HttpResponse(f"Welcome {request.user.username}!")


def generate_pkce_pair():
    """Generates a PKCE code_verifier and code_challenge."""
    code_verifier = (
        base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("utf-8")
    )

    sha256_hash = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(sha256_hash).rstrip(b"=").decode("utf-8")

    return code_verifier, code_challenge


# Authentication
def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            birthdate = form.cleaned_data["birthdate"]

            # Create a stripe customer
            stripe_customer_id = create_stripe_user(user)

            UserProfile.objects.create(
                user=user, birthdate=birthdate, stripe_customer_id=stripe_customer_id
            )

            return redirect("/accounts/login")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts-signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Generate a PKCE pair
            code_verifier, code_challenge = generate_pkce_pair()

            # Store the code verifier in the session
            request.session["code_verifier"] = code_verifier
            request.session["next"] = request.POST.get("next", "/")

            # Redirect to the OAuth2 authorization page after login
            client_id = settings.OAUTH2_AUTHORIZATION_CODE["client_id"]
            redirect_uri = settings.OAUTH2_AUTHORIZATION_CODE["redirect_uri"]

            oauth_url = (
                reverse("accounts:oauth2_provider:authorize")
                + f"?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&code_challenge={code_challenge}&code_challenge_method=S256"
            )

            return redirect(oauth_url)
        else:
            # Handle failed login (return an error, show a message, etc.)
            return HttpResponse("Invalid credentials", status=401)

    next = request.GET.get("next", "/")

    return render(request, "accounts-login.html", {"next": next})


def exchange_authorization_code_for_token(code, code_verifier):
    """Exchanges the authorization code for an access token."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OAUTH2_AUTHORIZATION_CODE["redirect_uri"],
        "client_id": settings.OAUTH2_AUTHORIZATION_CODE["client_id"],
        "client_secret": settings.OAUTH2_AUTHORIZATION_CODE["client_secret"],
        "code_verifier": code_verifier,
    }

    try:
        response = post(settings.OAUTH2_AUTHORIZATION_CODE["token_url"], data=data)

        if response.status_code != 200:
            logger.error(f"Error exchanging code for token: {response.text}")
            return None

        return response.json()  # Contains the access token and refresh token

    except Exception as e:
        logger.error(f"Error during token exchange: {str(e)}")
        return None


def exchange_client_credentials_for_token():
    """Exchanges client credentials for an access token."""
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.OAUTH2_CLIENT_CREDENTIALS["client_id"],
        "client_secret": settings.OAUTH2_CLIENT_CREDENTIALS["client_secret"],
    }

    try:
        response = post(settings.OAUTH2_CLIENT_CREDENTIALS["token_url"], data=data)

        if response.status_code != 200:
            logger.error(f"Error obtaining client credentials token: {response.text}")
            return None

        return response.json()  # Contains the access token

    except Exception as e:
        logger.error(f"Error during client credentials token exchange: {str(e)}")
        return None


def oauth2_callback(request):
    """Handle both Authorization Code Flow and Client Credentials Flow."""
    # Check if we're dealing with an authorization code flow or client credentials flow
    code = request.GET.get("code")
    code_verifier = request.session.get("code_verifier")
    client_credentials_flow = request.GET.get("client_credentials", False)

    logger.info(f"Received OAuth2 callback with code: {code}, client_credentials_flow: {client_credentials_flow}")

    if client_credentials_flow:
        # Client Credentials Flow
        token_data = exchange_client_credentials_for_token()
    elif code and code_verifier:
        # Authorization Code Flow
        token_data = exchange_authorization_code_for_token(code, code_verifier)
    else:
        logger.error("Missing code, code_verifier, or client_credentials flag.")
        return JsonResponse({"error": "Invalid request parameters"}, status=400)

    if token_data:
        # Successfully obtained an access token
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if access_token:
            # Store access token and refresh token in the session
            request.session["access_token"] = access_token
            request.session["expires_at"] = time.time() + expires_in

            if refresh_token:
                request.session["refresh_token"] = refresh_token

            next_url = request.session.get("next", "/")
            return redirect(next_url)

        else:
            logger.error("Access token not returned in the response.")
            return JsonResponse({"error": "No access token returned"}, status=400)

    else:
        logger.error("Failed to exchange code for token or obtain client credentials token.")
        return JsonResponse({"error": "Failed to obtain token"}, status=400)
    
    
def logout_view(request):
    logout(request)  # This logs out the user
    return redirect('/')
