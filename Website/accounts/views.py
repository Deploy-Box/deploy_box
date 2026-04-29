from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from accounts.serializers.UserCreationSerializer import UserCreationSerializer
from accounts.serializers.UserProfileSerializer import (
    UserProfileReadSerializer,
    UserProfileUpdateSerializer,
)
from accounts import services
from accounts.services import ServiceError, ValidationError
from django.conf import settings
import logging
from core.middleware import WorkOSSessionMiddleware

logger = logging.getLogger(__name__)


def _error_response(exc: ServiceError) -> Response:
    """Convert a service-layer exception into a DRF Response."""
    return Response({"error": str(exc)}, status=exc.status_code)


class SignupAPIView(APIView):
    def post(self, request):
        invite_id = request.data.get('invite_id')
        transfer_id = request.data.get('transfer_id')

        serializer = UserCreationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"user_errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if invite_id and transfer_id:
                result = services.signup_with_transfer(
                    validated_data=serializer.validated_data,
                    save_fn=serializer.save,
                    invite_id=invite_id,
                    transfer_id=transfer_id,
                )
            elif invite_id:
                result = services.signup_with_invite(
                    validated_data=serializer.validated_data,
                    save_fn=serializer.save,
                    invite_id=invite_id,
                )
            else:
                result = services.signup_regular(
                    validated_data=serializer.validated_data,
                    save_fn=serializer.save,
                )
        except ValidationError as exc:
            return Response(
                {"user_errors": {"general": [str(exc)]}},
                status=exc.status_code,
            )
        except ServiceError as exc:
            return Response(
                {"user_errors": {"general": [str(exc)]}},
                status=exc.status_code,
            )

        return Response(result, status=status.HTTP_201_CREATED)


class LogoutAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        workos_session_id = request.session.get("workos_session_id")
        request.session.flush()
        workos_logout_url = services.get_workos_logout_url(workos_session_id)

        return Response(
            {"detail": "Logged out successfully", "logout_url": workos_logout_url},
            status=status.HTTP_200_OK,
        )


class ProfileAPIView(APIView):
    """API view for user profile operations."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current user profile data."""
        serializer = UserProfileReadSerializer(request.user)
        return Response({"success": True, "user": serializer.data})

    def post(self, request):
        """Update user profile data."""
        serializer = UserProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            services.update_profile(request.user, serializer.validated_data)
        except ServiceError as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=exc.status_code,
            )

        return Response({"success": True, "message": "Profile updated successfully"})




class DeleteAccountAPIView(APIView):
    """API view for account deletion functionality."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        """Delete the authenticated user's account."""
        try:
            services.delete_account(request.user, request.session)
            return Response(
                {"success": True, "message": "Account deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Account deletion error: {e}")
            return Response(
                {"success": False, "error": "Failed to delete account"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WorkOSAuthInitiateView(APIView):
    """Initiate WorkOS AuthKit SSO flow."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Redirect user to WorkOS AuthKit hosted login."""
        from workos import WorkOSClient
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
        """Exchange authorization code for user profile, get-or-create local user, redirect."""
        from django.shortcuts import redirect

        try:
            code = request.GET.get("code")
            state = request.GET.get("state", "")

            # Exchange code for WorkOS user info
            workos_data = services.workos_authenticate(code)

            # Get or create local user
            user = services.get_or_create_workos_user(workos_data)

            # Extract session ID from access token
            workos_session_id = services.extract_workos_session_id(
                workos_data["access_token"]
            )

            # Establish session
            request.session.cycle_key()
            request.session[WorkOSSessionMiddleware.SESSION_KEY] = str(user.pk)
            if workos_session_id:
                request.session["workos_session_id"] = workos_session_id

            redirect_url = state if state else "/dashboard/"
            return redirect(redirect_url)

        except ServiceError as exc:
            logger.error(f"WorkOS callback error: {exc}")
            return redirect("/accounts/login/?error=workos_auth_failed")
        except Exception as e:
            logger.error(f"WorkOS callback error: {e}", exc_info=True)
            return redirect("/accounts/login/?error=workos_auth_failed")
