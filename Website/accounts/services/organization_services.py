from organizations.models import Organization, OrganizationMember
from django.contrib.auth.models import User
from django.http import (
    JsonResponse,
    HttpRequest,
)
import json


def add_collaborator(request: HttpRequest):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            org_id = data.get("org_id")
            user_id = data.get("user_id")

            user_exists = User.objects.filter(email=email).exists()

            if user_exists:
                organization = Organization.objects.filter(id=org_id).first()
                if organization:
                    check_member = OrganizationMember.objects.filter(organization_id=org_id, user_id=user_id).first()
                    if not check_member:
                        org_member = OrganizationMember.objects.create(
                            user_id=user_id,
                            organization_id=org_id,
                            role="member",
                        )
                        org_member.save()

                        return JsonResponse({"message": "user added to organization"}, status=200)
                    else:
                        return JsonResponse({"message": "user already added to organization"}, status=404)
                else:
                    return JsonResponse({"message": "organization does not exist"}, status=404)
            else:
                return JsonResponse({"message": "User does not exist"}, status=404)

        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

def remove_collaborator(request: HttpRequest):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data.get("user_id")
            org_id = data.get("org_id")

            check_collaborator = OrganizationMember.objects.filter(user_id=user_id, organization_id=org_id).exists()

            if check_collaborator:
                entry = OrganizationMember.objects.filter(user_id=user_id, organization_id=org_id)
                entry.delete()

                return JsonResponse({"message": "user has been removed"}, status=200)
            else:
                return JsonResponse({"message": "user is not associated with the provided organization"}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)