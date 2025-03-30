from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from accounts.models import UserProfile
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
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


logger = logging.getLogger(__name__)

@oauth_required
def protected_view(request):
    return HttpResponse(f"Welcome {request.user.username}!")

@oauth_required
def me(request):
    user = request.user
    return JsonResponse({"id": user.id, "username": user.username, "email": user.email})

def send_password_reset_email(email, reset_link):
    subject = "Password Reset Request"
    message = f"Click the link below to reset your password:\n\n{reset_link}\n\nIf you didn't request this, ignore this email."
    
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    
import uuid
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.loader import render_to_string
import json

User = get_user_model()

@csrf_exempt
@login_required
def update_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user = request.user  # Get the currently logged-in user

            # Normalize input values to lowercase for case-insensitive comparison
            new_email = data.get("email", "").strip().lower()
            new_username = data.get("username", "").strip().lower()

            if new_email and new_email != user.email.lower():
                # Check if the new email already exists
                if User.objects.filter(email__iexact=new_email).exists():
                    return JsonResponse({"error": "Email is already in use"}, status=400)
                
                # Generate a unique token for email verification
                token = uuid.uuid4().hex

                # Store the token in the UserProfile temporarily
                user_profile = UserProfile.objects.filter(user_id=user.id).first()  
                user_profile.email_verification_token = token
                user_profile.new_email = new_email
                user_profile.save()

                # Generate the verification link
                verification_url = request.build_absolute_uri(reverse("accounts:verify_email", args=[token]))

                # Send the verification email
                subject = "Verify Your New Email Address"
                message = render_to_string('accounts-email-verification.html', {
                    'user': user,
                    'verification_url': verification_url,
                })
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_email])

                return JsonResponse({"message": "A verification link has been sent to your new email."})
            
            if new_username and new_username != user.username.lower():
                if User.objects.filter(username__iexact=new_username).exists():
                    return JsonResponse({"error": "Username is already taken"}, status=400)
                user.username = new_username

            user.save()  # Save other updates

            return JsonResponse({"message": "Profile updated successfully!"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)
    

def verify_email(_, token):
    try:
        user_profile = UserProfile.objects.filter(email_verification_token=token).first()  
        user = User.objects.get(id=user_profile.user_id)

        # Email is verified, so update the user's email
        user.email = user_profile.new_email
        user_profile.email_verification_token = None  # Clear the token
        user_profile.new_email = None  # Clear the temporary email
        user.save()
        user_profile.save()

        return JsonResponse({"message": "Email successfully verified and updated."})
    except User.DoesNotExist:
        return JsonResponse({"error": "Invalid or expired token."}, status=400)


@csrf_exempt
def request_password_reset(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")
        
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"{settings.HOST}/accounts/reset-password/{uid}/{token}"

            if send_password_reset_email(email, reset_link):
                return JsonResponse({"message": "Password reset link sent!"})
            else:
                return JsonResponse({"error": "Failed to send email"}, status=500)
        
        except User.DoesNotExist:
            return JsonResponse({"error": "No account with this email"}, status=404)

@csrf_exempt
def reset_password(request, uidb64, token):
    if request.method == "POST":
        data = json.loads(request.body)
        new_password = data.get("password")

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)

            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return JsonResponse({"message": "Password reset successful!"})

            return JsonResponse({"error": "Invalid token"}, status=400)

        except (User.DoesNotExist, ValueError, TypeError):
            return JsonResponse({"error": "Invalid request"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


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

@oauth_required
def delete_user(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_name = data.get("user_name")
        if not user_name:
            return JsonResponse({"error": "user_name is required"}, status=400)

        try:
            user = User.objects.get(username=user_name)
            user.delete()
            return redirect('/')
        except ObjectDoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method. POST required."}, status=405)
