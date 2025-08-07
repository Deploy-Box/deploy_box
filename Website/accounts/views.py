from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from accounts.models import UserProfile
from accounts.serializers.UserCreationSerializer import UserCreationSerializer
from organizations.models import PendingInvites, OrganizationMember, Organization
from django.conf import settings
from django.db import transaction
from core.decorators.oauth_required import oauth_required
import requests
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class SignupAPIView(APIView):
    def post(self, request):
        invite_id = request.data.get('invite_id')
        transfer_id = request.data.get('transfer_id')
        
        if invite_id and transfer_id:
            # Handle combined invite + transfer signup
            return self._handle_transfer_signup(request, invite_id, transfer_id)
        elif invite_id:
            # Handle invite-based signup
            return self._handle_invite_signup(request, invite_id)
        else:
            # Handle regular signup
            return self._handle_regular_signup(request)
    
    def _handle_regular_signup(self, request):
        """Handle regular signup without organization creation."""
        user_serializer = UserCreationSerializer(data=request.data)

        if user_serializer.is_valid():
            with transaction.atomic():
                user = user_serializer.save()
                assert isinstance(user, UserProfile)

                # Check for pending invites
                user_email = user.email

                try:
                    invite = PendingInvites.objects.filter(email=user_email).first()
                    if invite:
                        org_id = invite.organization.id
                        organization = Organization.objects.get(id=org_id)

                        OrganizationMember.objects.create(user=user, organization=organization, role="member")

                        invite.delete()
                        
                        return Response(
                            {
                                "message": "User created and added to organization successfully",
                                "user_id": str(user.id),
                                "organization_id": str(organization.id),
                            },
                            status=status.HTTP_201_CREATED,
                        )
                    else:
                        # No pending invite found - just create the user
                        return Response(
                            {
                                "message": "User created successfully",
                                "user_id": str(user.id),
                            },
                            status=status.HTTP_201_CREATED,
                        )

                except Exception as e:
                    logger.error(f"Error processing pending invite: {e}")
                    return Response({"message": "Error processing invitation"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "user_errors": user_serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    def _handle_invite_signup(self, request, invite_id):
        """Handle signup with existing organization invite."""
        try:
            # Get the pending invite
            pending_invite = PendingInvites.objects.get(id=invite_id)
            
            # Validate that the email matches the invite
            if request.data.get('email') != pending_invite.email:
                return Response(
                    {
                        "user_errors": {
                            "email": ["Email must match the invited email address"]
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Create user without organization
            user_serializer = UserCreationSerializer(data=request.data)
            
            if user_serializer.is_valid():
                with transaction.atomic():
                    user = user_serializer.save()
                    assert isinstance(user, UserProfile)
                    
                    # Add user to the organization
                    OrganizationMember.objects.create(
                        organization=pending_invite.organization,
                        user=user,
                        role="member"
                    )
                    
                    # Remove the pending invite
                    pending_invite.delete()
                    
                    return Response(
                        {
                            "message": "User created and added to organization successfully",
                            "user_id": str(user.id),
                            "organization_id": str(pending_invite.organization.id),
                        },
                        status=status.HTTP_201_CREATED,
                    )
            else:
                return Response(
                    {
                        "user_errors": user_serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
                
        except PendingInvites.DoesNotExist:
            return Response(
                {
                    "user_errors": {
                        "invite": ["Invalid or expired invite link"]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error in invite signup: {e}")
            return Response(
                {
                    "user_errors": {
                        "general": ["An error occurred while processing your signup"]
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _handle_transfer_signup(self, request, invite_id, transfer_id):
        """Handle signup with both organization invite and project transfer."""
        try:
            # Get the pending invite
            pending_invite = PendingInvites.objects.get(id=invite_id)
            
            # Get the transfer invitation
            from organizations.models import ProjectTransferInvitation
            transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id, status="pending")
            
            # Validate that the email matches both the invite and transfer
            if request.data.get('email') != pending_invite.email or request.data.get('email') != transfer_invitation.to_email:
                return Response(
                    {
                        "user_errors": {
                            "email": ["Email must match the invited email address"]
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Create user
            user_serializer = UserCreationSerializer(data=request.data)
            
            if user_serializer.is_valid():
                with transaction.atomic():
                    user = user_serializer.save()
                    assert isinstance(user, UserProfile)
                    
                    # Add user to the organization
                    OrganizationMember.objects.create(
                        organization=pending_invite.organization,
                        user=user,
                        role="member"
                    )
                    
                    # Remove the pending invite
                    pending_invite.delete()
                    
                    # Automatically accept the project transfer
                    from organizations.services import accept_project_transfer
                    transfer_result = accept_project_transfer(transfer_id, user)
                    
                    if transfer_result.status_code == 200:
                        return Response(
                            {
                                "message": "Account created, organization joined, and project transfer completed successfully",
                                "user_id": str(user.id),
                                "organization_id": str(pending_invite.organization.id),
                                "transfer_completed": True
                            },
                            status=status.HTTP_201_CREATED,
                        )
                    else:
                        # Transfer failed but account was created
                        return Response(
                            {
                                "message": "Account created and organization joined, but project transfer failed. Please contact support.",
                                "user_id": str(user.id),
                                "organization_id": str(pending_invite.organization.id),
                                "transfer_completed": False
                            },
                            status=status.HTTP_201_CREATED,
                        )
            else:
                return Response(
                    {
                        "user_errors": user_serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
                
        except PendingInvites.DoesNotExist:
            return Response(
                {
                    "user_errors": {
                        "invite": ["Invalid or expired invite link"]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ProjectTransferInvitation.DoesNotExist:
            return Response(
                {
                    "user_errors": {
                        "transfer": ["Invalid or expired transfer invitation"]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error in transfer signup: {e}")
            return Response(
                {
                    "user_errors": {
                        "general": ["An error occurred while processing your signup"]
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutAPIView(APIView):
    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)


class OAuthPasswordLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        logger.info(f"Login attempt for user: {username}")

        user = authenticate(request, username=username, password=password)
        if user is None:
            logger.warning(f"Authentication failed for user: {username}")
            return Response({"detail": "Invalid credentials"}, status=400)

        logger.info(f"User authenticated successfully: {username}")
        login(request, user)

        token_url = settings.OAUTH2_PASSWORD_CREDENTIALS["token_url"]
        client_id = settings.OAUTH2_PASSWORD_CREDENTIALS["client_id"]
        client_secret = settings.OAUTH2_PASSWORD_CREDENTIALS["client_secret"]

        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        logger.info(f"Requesting OAuth token from: {token_url}")
        token_response = requests.post(token_url, data=payload)
        if token_response.status_code != 200:
            logger.error(
                f"Token request failed: {token_response.status_code} - {token_response.text}"
            )
            print("Token request failed:")
            print("Status Code:", token_response.status_code)
            print("Response Body:", token_response.text)
            return Response({"detail": "Token request failed"}, status=400)

        # Store token in session for web views
        token_data = token_response.json()
        logger.info(f"Token received successfully for user: {username}")
        logger.info(f"Token data keys: {list(token_data.keys())}")

        request.session["access_token"] = token_data.get("access_token")
        request.session["refresh_token"] = token_data.get("refresh_token")
        request.session.modified = True

        logger.info(f"Session access_token stored: {'access_token' in request.session}")
        logger.info(
            f"Session refresh_token stored: {'refresh_token' in request.session}"
        )
        logger.info(f"Session modified flag: {request.session.modified}")

        return Response(token_data)


class OAuthClientCredentialsView(APIView):
    """
    Machine-to-Machine authentication endpoint using OAuth2 client credentials flow.
    This endpoint allows services/applications to authenticate using their client credentials
    without user interaction.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        client_id = request.data.get("client_id")
        client_secret = request.data.get("client_secret")
        scope = request.data.get("scope", "m2m")

        logger.info(f"M2M authentication attempt for client: {client_id}")

        if not client_id or not client_secret:
            logger.warning("Missing client_id or client_secret in M2M request")
            return Response(
                {"detail": "client_id and client_secret are required"},
                status=400
            )

        token_url = settings.OAUTH2_CLIENT_CREDENTIALS["token_url"]

        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope,
        }

        logger.info(f"Requesting M2M OAuth token from: {token_url}")
        token_response = requests.post(token_url, data=payload)

        if token_response.status_code != 200:
            logger.error(
                f"M2M token request failed: {token_response.status_code} - {token_response.text}"
            )
            return Response(
                {"detail": "Client credentials authentication failed"},
                status=400
            )

        token_data = token_response.json()
        logger.info(f"M2M token received successfully for client: {client_id}")

        return Response(token_data)


class M2MProtectedView(APIView):
    """
    Example view that demonstrates M2M authentication.
    This view is protected and can only be accessed with valid client credentials.
    """

    @oauth_required(required_scope="m2m")
    def get(self, request):
        """
        Example GET endpoint that requires M2M authentication.
        """
        application = getattr(request, 'auth_application', None)
        token = getattr(request, 'auth_token', None)

        return Response({
            "message": "M2M authentication successful",
            "application": {
                "name": application.name if application else None,
                "client_id": application.client_id if application else None,
            },
            "token": {
                "expires": token.expires.isoformat() if token else None,
                "scope": token.scope if token else None,
            },
            "timestamp": timezone.now().isoformat(),
        })

    @oauth_required(required_scope="m2m")
    def post(self, request):
        """
        Example POST endpoint that requires M2M authentication.
        """
        return Response({
            "message": "M2M POST request successful",
            "timestamp": timezone.now().isoformat(),
        })


class ProfileAPIView(APIView):
    """API view for user profile operations."""

    @oauth_required()
    def get(self, request):
        """Get current user profile data."""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        user_data = {
            "username": request.user.username,
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        }

        return Response({
            "success": True,
            "user": user_data
        })

    @oauth_required()
    def post(self, request):
        """Update user profile data."""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        username = request.data.get('username')
        email = request.data.get('email')

        try:
            # Update username if provided and different
            if username and username != request.user.username:
                # Check if username is already taken
                if UserProfile.objects.filter(username=username).exclude(id=request.user.id).exists():
                    return Response({
                        "success": False,
                        "error": "Username is already taken"
                    }, status=status.HTTP_400_BAD_REQUEST)
                request.user.username = username

            # Update email if provided and different
            if email and email != request.user.email:
                # Check if email is already taken
                if UserProfile.objects.filter(email=email).exclude(id=request.user.id).exists():
                    return Response({
                        "success": False,
                        "error": "Email is already taken"
                    }, status=status.HTTP_400_BAD_REQUEST)
                request.user.email = email

            request.user.save()

            return Response({
                "success": True,
                "message": "Profile updated successfully"
            })

        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return Response({
                "success": False,
                "error": "Failed to update profile"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetAPIView(APIView):
    """API view for password reset functionality."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Send password reset email."""
        email = request.data.get('email')

        if not email:
            return Response({
                "success": False,
                "error": "Email is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if user exists
            user = UserProfile.objects.filter(email=email).first()
            if not user:
                # Don't reveal if email exists or not for security
                return Response({
                    "success": True,
                    "message": "If an account with that email exists, a password reset link has been sent."
                })

            # Use Django's built-in password reset functionality
            from django.contrib.auth.forms import PasswordResetForm
            from django.contrib.auth.tokens import default_token_generator
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes

            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Create reset URL
            reset_url = request.build_absolute_uri(
                f'/password_reset/confirm/{uid}/{token}/'
            )

            # Send email
            subject = "Password Reset Request"
            message = f"""
            Hello {user.username},

            You requested a password reset for your account. Please click the link below to reset your password:

            {reset_url}

            If you didn't request this, please ignore this email.

            Best regards,
            DeployBox Team
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,  # Use configured email
                [email],
                fail_silently=False,
            )

            return Response({
                "success": True,
                "message": "Password reset email sent successfully"
            })

        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return Response({
                "success": False,
                "error": "Failed to send password reset email"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetConfirmAPIView(APIView):
    """API view for password reset confirmation with token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        """Process password reset with token."""
        new_password1 = request.data.get('new_password1')
        new_password2 = request.data.get('new_password2')

        if not new_password1 or not new_password2:
            return Response({
                "success": False,
                "error": "Both password fields are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password1 != new_password2:
            return Response({
                "success": False,
                "error": "Passwords do not match"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_decode
            from django.utils.encoding import force_str
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError

            # Decode the user ID
            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = UserProfile.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, UserProfile.DoesNotExist):
                user = None

            if user is None:
                return Response({
                    "success": False,
                    "error": "Invalid reset link"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if the token is valid
            if not default_token_generator.check_token(user, token):
                return Response({
                    "success": False,
                    "error": "Invalid or expired reset link"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate the new password
            try:
                validate_password(new_password1, user)
            except ValidationError as e:
                return Response({
                    "success": False,
                    "error": "Password validation failed",
                    "details": list(e.messages)
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set the new password
            user.set_password(new_password1)
            user.save()

            return Response({
                "success": True,
                "message": "Password has been reset successfully"
            })

        except Exception as e:
            logger.error(f"Password reset confirmation error: {e}")
            return Response({
                "success": False,
                "error": "Failed to reset password"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAccountAPIView(APIView):
    """API view for account deletion functionality."""
    
    @oauth_required()
    def delete(self, request):
        """Delete the authenticated user's account."""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get the user to delete
            user = request.user
            
            # Log the user out first
            logout(request)
            
            # Delete the user account
            user.delete()
            
            return Response({
                "success": True,
                "message": "Account deleted successfully"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Account deletion error: {e}")
            return Response({
                "success": False,
                "error": "Failed to delete account"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
