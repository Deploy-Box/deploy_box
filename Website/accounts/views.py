import base64
import hashlib
import random
import string
import requests
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login
from django.http import (
    JsonResponse,
    HttpRequest,
    HttpResponseRedirect,
    HttpResponsePermanentRedirect,
)

from accounts.forms import CustomUserCreationForm, OrganizationSignUpForm
from organizations.models import PendingInvites

# Authentication
def signup(request: HttpRequest):
    if request.method == "POST":
        print(request.POST)
        user_form = CustomUserCreationForm(request.POST)
        org_form = OrganizationSignUpForm(request.POST)

        if user_form.is_valid() and org_form.is_valid():

            email = user_form.cleaned_data["email"]
            invites = PendingInvites.objects.filter(email=email)

            if invites.exists():  # Better to use `.exists()` to avoid loading all records into memory
                for invite in invites:
                    invite.delete()
            else:
                # Optional: handle the case where no invites are found (if needed)
                pass

            user = user_form.save()
            organization = org_form.save(user=user)

            print(f"Created user {user} and organization {organization}")

            return redirect("/login")

        return JsonResponse({"message": f"Invalid form data {user_form.is_valid()}{user_form.errors}, {org_form.is_valid()}"}, status=400)

    return JsonResponse({"message": "POST request required for signup"}, status=400)


def login_view(request: HttpRequest):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            # Handle missing username or password
            return JsonResponse(
                {"message": "Username and password are required"}, status=400
            )

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Login the user
            login(request, user)

            # Successful login
            # Use OAuth2 Password Grant to obtain an access token
            token_url = settings.OAUTH2_PASSWORD_CREDENTIALS["token_url"]
            client_id = settings.OAUTH2_PASSWORD_CREDENTIALS["client_id"]
            client_secret = settings.OAUTH2_PASSWORD_CREDENTIALS["client_secret"]

            if not token_url or not client_id or not client_secret:
                # Handle missing configuration for token request
                return JsonResponse(
                    {"message": "Token URL or client credentials not configured"},
                    status=500,
                )

            # Prepare the payload for the token request
            payload: dict[str, str] = {
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            # Make the token request
            print(f"Requesting token from {token_url} with payload: {payload}")
            response = requests.post(token_url, data=payload)

            if response.status_code != 200:
                return JsonResponse(
                    {"message": "Failed to obtain access token"}, status=400
                )

            # Parse the response and handle the token
            token = response.json()

            # Return the access token in the response
            request.session["access_token"] = token.get("access_token")
            request.session["refresh_token"] = token.get("refresh_token")

            # Check if access token was successfully obtained
            if not request.session["access_token"]:
                return JsonResponse(
                    {"message": "Failed to obtain access token from response"},
                    status=400,
                )

            # Redirect back to next page
            next_url = request.POST.get("next", "/")
            if next_url:
                # Redirect to the next URL if provided
                print(f"Redirecting to next URL: {next_url}")
                return HttpResponseRedirect(next_url)

            # If no next URL, redirect to a default page
            print("No next URL provided, redirecting to default page.")
            return HttpResponseRedirect("/")

        else:
            # Invalid credentials
            return JsonResponse({"message": "Invalid credentials"}, status=400)

    return JsonResponse({"message": "POST request required"}, status=400)


# Helper functions for PKCE
def generate_code_verifier():
    """Generates a code verifier for PKCE."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=43))


def generate_code_challenge(code_verifier: str) -> str:
    """Generates a code challenge using the S256 method."""
    code_verifier_bytes = code_verifier.encode("utf-8")
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier_bytes).digest())
        .decode("utf-8")
        .rstrip("=")
    )
    return code_challenge


# Step 1: Authorization Request
def oauth_authorize(
    request: HttpRequest,
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    # Save the code_verifier in the session to use it later during token exchange
    request.session["code_verifier"] = code_verifier

    # Redirect to OAuth2 provider's authorization endpoint
    authorization_url = f"{settings.OAUTH2_PROVIDER['AUTHORIZATION_URL']}?response_type=code&client_id={settings.OAUTH2_AUTHORIZATION_CODE['client_id']}&redirect_uri={settings.OAUTH2_AUTHORIZATION_CODE['redirect_uri']}&code_challenge={code_challenge}&code_challenge_method=S256"

    return redirect(authorization_url)


# Step 2: Callback and Token Exchange
def oauth_callback(request: HttpRequest) -> JsonResponse:
    code = request.GET.get("code")
    code_verifier = request.session.get("code_verifier")

    if not code or not code_verifier:
        return JsonResponse({"error": "Missing code or code_verifier"}, status=400)

    # Exchange the authorization code for an access token
    token_url = settings.OAUTH2_AUTHORIZATION_CODE["token_url"]
    client_id = settings.OAUTH2_AUTHORIZATION_CODE["client_id"]
    client_secret = settings.OAUTH2_AUTHORIZATION_CODE["client_secret"]
    redirect_uri = settings.OAUTH2_AUTHORIZATION_CODE["redirect_uri"]

    # Prepare the payload for the token request
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": code_verifier,
    }

    # Make the token request
    response = requests.post(token_url, data=payload)

    if response.status_code != 200:
        return JsonResponse({"error": "Failed to obtain access token"}, status=400)

    # Parse the response and handle the token
    tokens = response.json()

    # You can store the tokens (e.g., access token) in session, database, etc.
    request.session["access_token"] = tokens.get("access_token")
    request.session["refresh_token"] = tokens.get("refresh_token")

    return JsonResponse(tokens)


def logout_view(request: HttpRequest) -> JsonResponse | HttpResponseRedirect:
    """
    Handle user logout by clearing the session and redirecting to the login page.
    """
    # Clear the session
    request.session.flush()

    # Redirect to the login page
    return HttpResponseRedirect("/")

# @oauth_required()
# def add_org_members(request: HttpRequest) -> JsonResponse:
#     return organization_services.add_collaborator(request)


# @oauth_required()
# def remove_org_member(request: HttpRequest) -> JsonResponse:
#     return organization_services.remove_collaborator(request)


# @oauth_required()
# def create_project(request: HttpRequest) -> JsonResponse:
#     return project_services.create_project(request)


# @oauth_required()
# def update_project(request: HttpRequest) -> JsonResponse:
#     return project_services.update_project(request)


# @oauth_required()
# def delete_project(request: HttpRequest) -> JsonResponse:
#     return project_services.delete_project(request)


# @oauth_required()
# def add_project_members(request: HttpRequest) -> JsonResponse:
#     return project_services.add_project_members(request)


# @oauth_required()
# def delete_project_member(request: HttpRequest) -> JsonResponse:
#     return project_services.delete_project_member(request)
