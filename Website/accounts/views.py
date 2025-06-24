from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login
from accounts.serializers.UserCreationSerializer import UserCreationSerializer
from accounts.serializers.OrganizationSignupSerializer import OrganizationSignupSerializer
from organizations.models import PendingInvites, OrganizationMember, Organization
from django.conf import settings
from django.db import transaction
import requests


class SignupAPIView(APIView):
    def post(self, request):
        user_serializer = UserCreationSerializer(data=request.data)
        org_serializer = OrganizationSignupSerializer(data=request.data, context={"user": None})  # placeholder

        user_serializer_is_valid = user_serializer.is_valid()
        org_serializer_is_valid = org_serializer.is_valid()

        if user_serializer_is_valid and org_serializer_is_valid:
            with transaction.atomic():
                user = user_serializer.save()
                org_serializer.context["user"] = user
                org = org_serializer.save()

                return Response(
                    {"message": "User and organization created", "user": user.username, "organization": org},
                    status=status.HTTP_201_CREATED
                )

        return Response({
            "user_errors": user_serializer.errors,
            "org_errors": org_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    

class OAuthPasswordLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=400)

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

        token_response = requests.post(token_url, data=payload)
        if token_response.status_code != 200:
            print("Token request failed:")
            print("Status Code:", token_response.status_code)
            print("Response Body:", token_response.text)
            return Response({"detail": "Token request failed"}, status=400)

        return Response(token_response.json())

class OAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.GET.get("code")
        code_verifier = request.session.get("code_verifier")

        if not code or not code_verifier:
            return Response({"error": "Missing code or verifier"}, status=400)

        token_url = settings.OAUTH2_AUTHORIZATION_CODE["token_url"]
        client_id = settings.OAUTH2_AUTHORIZATION_CODE["client_id"]
        client_secret = settings.OAUTH2_AUTHORIZATION_CODE["client_secret"]
        redirect_uri = settings.OAUTH2_AUTHORIZATION_CODE["redirect_uri"]

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier,
        }

        token_response = requests.post(token_url, data=payload)
        if token_response.status_code != 200:
            return Response({"error": "Token exchange failed"}, status=400)

        request.session["access_token"] = token_response.json().get("access_token")
        request.session["refresh_token"] = token_response.json().get("refresh_token")

        return Response(token_response.json())
