from accounts.models import Organization, OrganizationMember
from django.contrib.auth.models import User
from django.http import (
    JsonResponse,
    HttpRequest,
    HttpResponseRedirect,
    HttpResponsePermanentRedirect,
)
import requests
import json

def create_organization(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name").lower()

            Organization.objects.create(name=name)

            return JsonResponse({"message": "organization created"}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
        
def update_organization(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            org_id = data.get("organization_id")

            org = Organization.objects.get(id=org_id)

            if org:
                org.name = data.get("name", org.name).lower()
                org.save()

                return JsonResponse({"message": "organization updated"}, status=200)
            else:
                return JsonResponse({"message": "organization not found, unable to update"}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
        

def delete_organization(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body)
        org_id = data.get("organization_id")

        if org_id:
            org = Organization.objects.filter(id=org_id).first()
            if org:
                org.delete()
                return JsonResponse({"message": "organization deleted"}, status=200)
            else:
                return JsonResponse({"message": "organization does not exist"}, status=404)
        else:
            return JsonResponse({"message": "organization id was not provided"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)






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