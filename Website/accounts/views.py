from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login
from accounts.models import UserProfile
from accounts.serializers.UserCreationSerializer import UserCreationSerializer
from accounts.serializers.OrganizationSignupSerializer import (
    OrganizationSignupSerializer,
)
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
        user_serializer = UserCreationSerializer(data=request.data)
        org_serializer = OrganizationSignupSerializer(
            data=request.data, context={"user": None}
        )  # placeholder

        user_serializer_is_valid = user_serializer.is_valid()
        org_serializer_is_valid = org_serializer.is_valid()

        if user_serializer_is_valid and org_serializer_is_valid:
            with transaction.atomic():
                user = user_serializer.save()
                assert isinstance(user, UserProfile)
                org_serializer.context["user"] = user
                org = org_serializer.save()
                assert isinstance(org, Organization)

                # Create a simple serializable response
                return Response(
                    {
                        "message": "User and organization created successfully",
                        "user_id": str(user.id),
                        "organization_id": str(org.id),
                    },
                    status=status.HTTP_201_CREATED,
                )

        return Response(
            {
                "user_errors": user_serializer.errors,
                "org_errors": org_serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


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
        application = getattr(request, 'auth_application', None)
        
        return Response({
            "message": "M2M POST request successful",
            "application": application.name if application else None,
            "data_received": request.data,
            "timestamp": timezone.now().isoformat(),
        })
