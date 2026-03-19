from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from accounts.models import UserProfile
from accounts.serializers.UserCreationSerializer import UserCreationSerializer
from organizations.models import PendingInvites, OrganizationMember, Organization
from django.conf import settings
from django.db import transaction
import logging
from workos import WorkOSClient
from core.middleware import WorkOSSessionMiddleware

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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Capture WorkOS session ID before clearing the Django session
        workos_session_id = request.session.get("workos_session_id")

        # Clear the Django session (removes _workos_user_id and all session data)
        request.session.flush()

        # Build a WorkOS logout URL so the frontend can clear the AuthKit session.
        # In dev, skip the WorkOS redirect — localhost isn't whitelisted as a
        # return URL in WorkOS, which causes a redirect to production.
        workos_logout_url = None
        if workos_session_id and settings.ENV != "DEV":
            try:
                workos_client = WorkOSClient(
                    api_key=settings.WORKOS["API_KEY"],
                    client_id=settings.WORKOS["CLIENT_ID"],
                )
                workos_logout_url = workos_client.user_management.get_logout_url(
                    session_id=workos_session_id,
                    return_to=settings.HOST,
                )
            except Exception as e:
                logger.warning(f"Failed to build WorkOS logout URL: {e}")

        return Response(
            {"detail": "Logged out successfully", "logout_url": workos_logout_url},
            status=status.HTTP_200_OK,
        )





class ProfileAPIView(APIView):
    """API view for user profile operations."""

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




class DeleteAccountAPIView(APIView):
    """API view for account deletion functionality."""
    
    def delete(self, request):
        """Delete the authenticated user's account."""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get the user to delete
            user = request.user
            
            # Log the user out first
            request.session.flush()
            
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


class WorkOSAuthInitiateView(APIView):
    """Initiate WorkOS AuthKit SSO flow."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Redirect user to WorkOS AuthKit hosted login."""
        try:
            workos_client = WorkOSClient(
                api_key=settings.WORKOS["API_KEY"],
                client_id=settings.WORKOS["CLIENT_ID"],
            )

            redirect_uri = settings.WORKOS["REDIRECT_URI"]
            state = request.GET.get("state", "")

            authorization_url = workos_client.user_management.get_authorization_url(
                provider="authkit",
                redirect_uri=redirect_uri,
                state=state or None,
            )

            from django.shortcuts import redirect
            return redirect(authorization_url)

        except Exception as e:
            logger.error(f"WorkOS auth initiation error: {e}")
            return Response(
                {"error": "Failed to initiate WorkOS authentication"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WorkOSAuthCallbackView(APIView):
    """Handle WorkOS AuthKit callback."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Exchange authorization code for user profile, get-or-create local user, mint DOT token, redirect."""
        try:
            code = request.GET.get("code")
            state = request.GET.get("state", "")

            if not code:
                logger.warning("WorkOS callback missing authorization code")
                return Response(
                    {"error": "Authorization code not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Exchange code for user info via WorkOS SDK ──
            workos_client = WorkOSClient(
                api_key=settings.WORKOS["API_KEY"],
                client_id=settings.WORKOS["CLIENT_ID"],
            )

            auth_response = workos_client.user_management.authenticate_with_code(
                code=code,
                session=None,
            )

            workos_user = auth_response.user
            workos_user_id = workos_user.id
            email = workos_user.email
            first_name = workos_user.first_name or ""
            last_name = workos_user.last_name or ""

            if not email:
                logger.error("WorkOS user has no email address")
                return Response(
                    {"error": "Email not available from WorkOS"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Get-or-create local UserProfile ──
            # First try matching by workos_user_id, then by email
            user = UserProfile.objects.filter(workos_user_id=workos_user_id).first()

            if not user:
                user = UserProfile.objects.filter(email=email).first()
                if user:
                    # Link existing account to WorkOS
                    user.workos_user_id = workos_user_id
                    user.auth_provider = "workos"
                    user.save(update_fields=["workos_user_id", "auth_provider"])
                    logger.info(f"Linked existing user {user.username} to WorkOS ID {workos_user_id}")

            if not user:
                # Create a brand-new user
                base_username = email.split("@")[0]
                username = base_username
                counter = 1
                while UserProfile.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = UserProfile.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    workos_user_id=workos_user_id,
                    auth_provider="workos",
                )
                # Set an unusable password — this user authenticates via WorkOS
                user.set_unusable_password()
                user.save()
                logger.info(f"Created new user {username} via WorkOS")

                # Check for pending org invites for this email
                try:
                    invite = PendingInvites.objects.filter(email=email).first()
                    if invite:
                        OrganizationMember.objects.create(
                            user=user,
                            organization=invite.organization,
                            role="member",
                        )
                        invite.delete()
                        logger.info(f"Auto-joined user {username} to org via pending invite")
                except Exception as inv_err:
                    logger.error(f"Error processing pending invite for WorkOS user: {inv_err}")

            # ── Extract WorkOS session ID from the access token JWT ──
            try:
                import jwt as pyjwt
                decoded = pyjwt.decode(
                    auth_response.access_token,
                    options={"verify_signature": False},
                )
                workos_session_id = decoded.get("sid")
            except Exception as jwt_err:
                logger.warning(f"Could not decode WorkOS access_token JWT: {jwt_err}")
                workos_session_id = None

            # ── WorkOS session login (replaces Django's login()) ──
            request.session.cycle_key()  # prevent session fixation
            request.session[WorkOSSessionMiddleware.SESSION_KEY] = str(user.pk)

            # ── Store WorkOS session ID so we can build a logout URL later ──
            if workos_session_id:
                request.session["workos_session_id"] = workos_session_id

            # ── Redirect ──
            from django.shortcuts import redirect
            redirect_url = state if state else "/dashboard/"
            return redirect(redirect_url)

        except Exception as e:
            logger.error(f"WorkOS callback error: {e}", exc_info=True)
            from django.shortcuts import redirect
            return redirect("/accounts/login/?error=workos_auth_failed")
