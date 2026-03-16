from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import os
import json
import hashlib
import secrets
from deploy_box_apis.models import APICredential, API, APIUsage, APIKey
from typing import Any, Dict, List, Optional, TypedDict
import os
from django.db.models import OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

def generate(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse({"error": "Project ID is required, got: " + " ".join(list(request.POST.keys()))}, status=400)
    # Check if a credential already exists for this project
    existing_credential = APICredential.objects.filter(project_id=project_id).first()
    if existing_credential:
        return JsonResponse({
            "client_id": existing_credential.client_id,
            "client_secret_hint": existing_credential.client_secret_hint
        })


    os.environ.get('DEPLOY_BOX_API_BASE_URL').rstrip('/')

    url = f"{os.environ.get('DEPLOY_BOX_API_BASE_URL')}/api/client_self_service/generate"

    body = {
        "project_id": project_id
    }

    response = requests.post(url, json=body)

    if response.status_code != 200:
        raise Exception(f"Error generating API key: {response.text}")
    
    data = response.json()

    client_secret_hint = data['client_secret'][:4] + "..." + data['client_secret'][-4:]

    new_credential = APICredential(
        project_id=project_id,
        client_id=data['client_id'],
        client_secret=data['client_secret'],
        client_secret_hint=client_secret_hint
    )

    new_credential.save()

    return JsonResponse({
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
        "client_secret_hint": client_secret_hint
    })
    
       
def revoke(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse({"error": "Project ID is required, got: " + " ".join(list(request.POST.keys()))}, status=400)
    # Check if a credential already exists for this project
    existing_credential = APICredential.objects.filter(project_id=project_id).first()
    if not existing_credential:
        return JsonResponse({"error": "No API key found for this project"}, status=404)

    os.environ.get('DEPLOY_BOX_API_BASE_URL').rstrip('/')

    url = f"{os.environ.get('DEPLOY_BOX_API_BASE_URL')}/api/client_self_service/revoke"

    body = {
        "project_id": project_id
    }

    response = requests.post(url, json=body)

    if response.status_code not in (204, 404):
        raise Exception(f"Error revoking API key: {response.text}")
    
    existing_credential.delete()

    return JsonResponse({"status": "API key revoked successfully"})
    

def rotate(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse({"error": "Project ID is required, got: " + " ".join(list(request.POST.keys()))}, status=400)
    # Check if a credential already exists for this project
    existing_credential = APICredential.objects.filter(project_id=project_id).first()
    if not existing_credential:
        return JsonResponse({"error": "No API key found for this project"}, status=404)

    os.environ.get('DEPLOY_BOX_API_BASE_URL').rstrip('/')

    url = f"{os.environ.get('DEPLOY_BOX_API_BASE_URL')}/api/client_self_service/rotate"

    body = {
        "project_id": project_id
    }

    response = requests.post(url, json=body)

    if response.status_code != 200:
        raise Exception(f"Error rotating API key: {response.text}")

    data = response.json()

    client_secret_hint = data['client_secret'][:4] + "..." + data['client_secret'][-4:]

    existing_credential.client_id = data['client_id']
    existing_credential.client_secret = data['client_secret']
    existing_credential.client_secret_hint = client_secret_hint
    existing_credential.save()

    return JsonResponse({
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
        "client_secret_hint": client_secret_hint
    })

def generate_token(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse({"error": "Project ID is required, got: " + " ".join(list(request.POST.keys()))}, status=400)
    # Check if a credential already exists for this project
    existing_credential = APICredential.objects.filter(project_id=project_id).first()
    if not existing_credential:
        return JsonResponse({"error": "No API key found for this project"}, status=404)

    os.environ.get('DEPLOY_BOX_API_BASE_URL').rstrip('/')

    url = f"{os.environ.get('DEPLOY_BOX_API_BASE_URL')}/api/client_self_service/oauth2/token"

    body = {
        "grant_type": "client_credentials",
        "client_id": existing_credential.client_id,
        "client_secret": existing_credential.client_secret,
    }

    response = requests.post(url, json=body)

    if response.status_code != 200:
        print(response.text, response.status_code, url, body)
        raise Exception(f"Error generating token: {response.text} {response.status_code}")

    data = response.json()

    return JsonResponse({
        "access_token": data["access_token"],
        "token_type": data["token_type"],
        "expires_in": data["expires_in"],
    })

def increment_api_usage(request: HttpRequest):
    from deploy_box_apis.models import APIUsage, API
    from projects.models import Project

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body).get("data")
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    if not data:
        return JsonResponse({"error": "Data is required"}, status=400)
    
    client_id = data.get("client_id")
    api_id = data.get("api_id")

    print(data)

    if not client_id or not api_id:
        return JsonResponse({"error": "client_id and api_id are required"}, status=400)
    
    api_credential = APICredential.objects.filter(client_id=client_id).first()
    if not api_credential:
        return JsonResponse({"error": "Invalid client_id"}, status=400)
    
    project_id = api_credential.project_id

    try:
        project = Project.objects.get(id=project_id)
        api = API.objects.get(api_key=api_id)
    except Project.DoesNotExist:
        raise Exception(f"Project with ID {project_id} does not exist.")
    except API.DoesNotExist:
        raise Exception(f"API with ID {api_id} does not exist.")

    api_usage, _ = APIUsage.objects.get_or_create(project=project, api=api)
    api_usage.usage_count += 1
    from django.utils import timezone
    api_usage.last_used_at = timezone.now()
    api_usage.save()
    return JsonResponse({"usage_count": api_usage.usage_count})

class APIItem(TypedDict, total=False):
    id: int
    name: str
    description: str
    price_per_1000_requests: Any  # Decimal; serialize as needed
    endpoint: str
    icon: str
    category: str
    popular: bool
    response_time: Any  # Decimal/float
    features: Any       # JSONField/dict/list
    usage_count: int

class APIInfo(TypedDict):
    available_apis: List[APIItem]
    api_key: Optional[Dict[str, str]]
    base_url: Optional[str]

def get_project_api_info(project_id: str) -> APIInfo:
    # Subquery to sum usage per API for this project
    usage_subq = (
        APIUsage.objects
        .filter(project_id=project_id, api_id=OuterRef("pk"))
        .values("api_id")
        .annotate(total=Sum("usage_count"))
        .values("total")[:1]
    )

    # Single query: pull API fields and annotate usage_count (default 0)
    available_apis_qs = (
        API.objects
        .values(
            "id", "name", "description", "price_per_1000_requests",
            "endpoint", "icon", "category", "popular", "response_time", "features"
        )
        .annotate(usage_count=Coalesce(Subquery(usage_subq), Value(0)))
        # .order_by("name")  # add ordering if you want deterministic output
    )
    available_apis: List[APIItem] = list(available_apis_qs)

    # Credentials (limit columns)
    cred = (
        APICredential.objects
        .filter(project_id=project_id)
        .only("client_id", "client_secret_hint")
        .first()
    )
    api_key: Optional[Dict[str, str]] = None
    if cred:
        api_key = {
            "client_id": cred.client_id,
            "client_secret": cred.client_secret,
            "client_secret_hint": cred.client_secret_hint,
        }

    # Base URL (safe handling)
    base_url_env = os.getenv("DEPLOY_BOX_API_BASE_URL")
    base_url = base_url_env.rstrip("/") if base_url_env else None

    return {
        "available_apis": available_apis,
        "api_key": api_key,
        "base_url": base_url,
        "token_endpoint": base_url + "/oauth2/token" if base_url else None,
    }


# --------------- Public API Key management ---------------

def _generate_raw_key() -> str:
    """Generate a Google-style public API key: dbx_ + 40 URL-safe chars."""
    return "dbx_" + secrets.token_urlsafe(30)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _key_hint(raw_key: str) -> str:
    return raw_key[:8] + "..." + raw_key[-4:]


@csrf_exempt
def generate_api_key(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST

    project_id = body.get("project_id")
    name = body.get("name", "Default")

    if not project_id:
        return JsonResponse({"error": "project_id is required"}, status=400)

    raw_key = _generate_raw_key()

    api_key_obj = APIKey(
        project_id=project_id,
        name=name,
        key_hash=_hash_key(raw_key),
        key_hint=_key_hint(raw_key),
    )
    api_key_obj.save()

    return JsonResponse({
        "id": api_key_obj.id,
        "name": api_key_obj.name,
        "api_key": raw_key,
        "key_hint": api_key_obj.key_hint,
        "message": "Store this key securely — it will not be shown again.",
    })


@csrf_exempt
def revoke_api_key(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST

    key_id = body.get("key_id")
    project_id = body.get("project_id")

    if not key_id or not project_id:
        return JsonResponse({"error": "key_id and project_id are required"}, status=400)

    api_key_obj = APIKey.objects.filter(id=key_id, project_id=project_id, is_active=True).first()
    if not api_key_obj:
        return JsonResponse({"error": "API key not found or already revoked"}, status=404)

    api_key_obj.is_active = False
    api_key_obj.save()

    return JsonResponse({"status": "API key revoked"})


def list_api_keys(request: HttpRequest):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    project_id = request.GET.get("project_id")
    if not project_id:
        return JsonResponse({"error": "project_id query param is required"}, status=400)

    keys = APIKey.objects.filter(project_id=project_id).values(
        "id", "name", "key_hint", "is_active", "created_at"
    )
    return JsonResponse({"api_keys": list(keys)})


@csrf_exempt
def validate_api_key(request: HttpRequest):
    """Internal endpoint called by the Functions app to validate a public API key."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    raw_key = body.get("api_key", "")
    if not raw_key:
        return JsonResponse({"valid": False, "error": "api_key is required"}, status=400)

    key_hash = _hash_key(raw_key)
    api_key_obj = APIKey.objects.filter(key_hash=key_hash, is_active=True).select_related("project").first()

    if not api_key_obj:
        return JsonResponse({"valid": False}, status=404)

    return JsonResponse({
        "valid": True,
        "project_id": api_key_obj.project_id,
        "key_id": api_key_obj.id,
        "key_name": api_key_obj.name,
    })