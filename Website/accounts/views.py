import base64
import hashlib
import random
import string
import requests
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login
from django.http import (
    JsonResponse,
    HttpRequest,
    HttpResponseRedirect,
    HttpResponsePermanentRedirect,
    HttpResponse,
)
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from django.contrib import messages

from accounts.forms import CustomUserCreationForm, OrganizationSignUpForm, User
from organizations.models import PendingInvites, OrganizationMember, Organization


# Authentication
def signup(request: HttpRequest):
    if request.method == "POST":
        print(request.POST)
        user_form = CustomUserCreationForm(request.POST)
        org_form = OrganizationSignUpForm(request.POST)

        if user_form.is_valid() and org_form.is_valid():

            email = user_form.cleaned_data["email"]
            invites = PendingInvites.objects.filter(email__iexact=email)

            user = user_form.save()
            organization = org_form.save(user=user)

            if (
                invites.exists()
            ):  # Better to use `.exists()` to avoid loading all records into memory
                for invite in invites:
                    org_id = invite.organization_id  # type: ignore
                    org_to_add = Organization.objects.get(id=org_id)
                    organization_member = OrganizationMember.objects.create(
                        user=user, organization=org_to_add, role="member"
                    )
                    print(organization_member)
                    invite.delete()
            else:
                # Optional: handle the case where no invites are found (if needed)
                pass

            print(f"Created user {user} and organization {organization}")

            return redirect("/login")

        return JsonResponse(
            {
                "message": f"Invalid form data {user_form.is_valid()}{user_form.errors}, {org_form.is_valid()}"
            },
            status=400,
        )

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


def password_reset(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            messages.error(request, "Email is required.")
            return render(request, "accounts/password_reset.html", {})

        try:
            user = User.objects.get(email=email)
            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Create reset link
            reset_link = f"{request.scheme}://{request.get_host()}/password_reset/confirm/{uid}/{token}/"

            # Send email
            subject = "Password Reset Request"
            message = f"""
            Hello {user.username},

            You're receiving this email because you requested a password reset for your Deploy Box account.

            Please go to the following page and choose a new password:
            {reset_link}

            If you didn't request this, you can safely ignore this email.

            Best regards,
            Deploy Box Team
            """

            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            send_mail(subject, message, from_email, recipient_list, fail_silently=False)

            print("Reset link: ", reset_link)
            print(f"Password reset email sent to {user.email} from {from_email}")

            messages.success(
                request, "Password reset email has been sent. Please check your inbox."
            )
            return redirect("main_site:login")

        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            messages.success(
                request,
                "If an account exists with this email, you will receive a password reset link.",
            )
            print(f"Email {email} does not exist")
            return redirect("main_site:login")

    return render(request, "accounts/password_reset.html", {})


def password_reset_confirm(
    request: HttpRequest, uidb64: str, token: str
) -> HttpResponse:
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            new_password1 = request.POST.get("new_password1")
            new_password2 = request.POST.get("new_password2")

            if not new_password1 or not new_password2:
                messages.error(request, "Both password fields are required.")
                return render(request, "accounts/password_reset_confirm.html", {})

            if new_password1 != new_password2:
                messages.error(request, "The two password fields didn't match.")
                return render(request, "accounts/password_reset_confirm.html", {})

            if len(new_password1) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return render(request, "accounts/password_reset_confirm.html", {})

            user.set_password(new_password1)
            user.save()
            messages.success(
                request,
                "Your password has been successfully reset. You can now log in with your new password.",
            )
            return redirect("main_site:login")

        return render(request, "accounts/password_reset_confirm.html", {})
    else:
        messages.error(request, "The password reset link is invalid or has expired.")
        return redirect("main_site:password_reset")
