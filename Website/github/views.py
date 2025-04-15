import requests
import hmac
import hashlib
import secrets
import threading

from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string

from core.decorators import oauth_required, AuthHttpRequest
from core.helpers import assertRequiredFields
from core.utils import GCPUtils
from github.models import Webhook, Token
from stacks.models import Stack

# GitHub OAuth credentials
CLIENT_ID = settings.GITHUB.get("CLIENT_ID")
CLIENT_SECRET = settings.GITHUB.get("CLIENT_SECRET")
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_REPOS_URL = "https://api.github.com/user/repos"


def home(_: HttpRequest) -> HttpResponse:
    return HttpResponse(
        "Welcome to Deploy Box! <a href='/github/auth'>Login with GitHub</a>"
    )


def github_login(_: HttpRequest) -> HttpResponse:
    """Redirects users to GitHub OAuth page."""
    return redirect(f"{GITHUB_AUTH_URL}?client_id={CLIENT_ID}&scope=repo")


def github_callback(request: HttpRequest) -> HttpResponse:
    """Handles GitHub OAuth callback and fetches user info."""
    code = request.GET.get("code")
    if not code:
        return HttpResponse("Authorization failed", status=400)

    # Exchange code for access token
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code},
    )
    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return HttpResponse("Failed to retrieve access token", status=400)

    # Fetch user info from GitHub API
    user_response = requests.get(
        GITHUB_USER_URL, headers={"Authorization": f"token {access_token}"}
    )
    user_data = user_response.json()

    if "id" not in user_data:
        return HttpResponse("Failed to retrieve user info", status=400)

    # Store token securely in database
    github_token, created = Token.objects.get_or_create(user=request.user)
    github_token.set_token(access_token)
    github_token.save()

    # Store user info in session
    request.session["github_user"] = user_data
    request.session.modified = True

    return redirect(reverse("github:list_repos"))


def dashboard(request: HttpRequest) -> HttpResponse:
    """Displays user info after successful login."""
    if "github_user" not in request.session:
        return redirect(reverse("github:home"))

    user = request.session["github_user"]
    return HttpResponse(f"Welcome, {user['login']}! <a href='/logout'>Logout</a>")


def logout(request: HttpRequest) -> HttpResponse:
    """Clears session data."""
    request.session.clear()
    return redirect(reverse("github:home"))


def list_repos(request: HttpRequest) -> HttpResponse:
    """Fetch and display user repositories with a deploy button."""
    user = request.user

    # Retrieve GitHub token securely
    try:
        github_token = Token.objects.get(user=user).get_token()
    except Token.DoesNotExist:
        return JsonResponse({"error": "GitHub token not found"}, status=403)

    repo_response = requests.get(
        GITHUB_REPOS_URL,
        headers={"Authorization": f"token {github_token}"},
        params={"per_page": 100},
    )

    if repo_response.status_code != 200:
        return JsonResponse({"error": "Failed to fetch repositories"}, status=400)

    repos = repo_response.json()

    # Fetch user stacks
    stacks = Stack.objects.filter(user=user)
    if not stacks.exists():
        return JsonResponse({"error": "No stacks available"}, status=404)

    # Safely render repositories list with deploy button
    repo_list_html = "<h2>Your GitHub Repositories:</h2><ul>"

    for repo in repos:
        # Rendering each repo item with deploy button
        repo_list_html += render_to_string(
            "repo_list_item.html",
            {
                "repo_name": repo["name"],
                "repo_url": repo["html_url"],
                "repo_clone_url": repo["clone_url"],
                "stacks": stacks,
            },
        )

    repo_list_html += "</ul>"

    return HttpResponse(repo_list_html)


import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

GITHUB_API_BASE = "https://api.github.com"


def create_github_webhook(request: HttpRequest) -> JsonResponse:
    """Create and store a GitHub webhook for a user's repository."""
    user = request.user
    repo_name = request.POST.get("repo-name")
    stack_id = request.POST.get("stack-id")

    if not repo_name or not stack_id:
        return JsonResponse(
            {"error": "Repository name and Stack ID are required"}, status=400
        )

    stack = Stack.objects.filter(id=stack_id).first()
    if not stack:
        return JsonResponse({"error": "Stack not found"}, status=404)

    try:
        github_token = Token.objects.get(user=user).get_token()
    except Token.DoesNotExist:
        return JsonResponse({"error": "GitHub token not found"}, status=403)

    headers = {"Authorization": f"token {github_token}"}
    try:
        response = requests.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"GitHub API request failed: {str(e)}"}, status=400
        )

    github_username = response.json().get("login")

    # Verify repository existence
    repo_check_url = f"{GITHUB_API_BASE}/repos/{github_username}/{repo_name}"
    repo_response = requests.get(repo_check_url, headers=headers)
    if repo_response.status_code != 200:
        return JsonResponse(
            {"error": "Repository not found or access denied"}, status=404
        )

    # Generate a unique webhook secret
    webhook_secret = secrets.token_hex(32)

    # Webhook URL
    webhook_url = f"{settings.HOST}/github/webhook"

    payload = {
        "name": "web",
        "active": True,
        "events": ["push"],
        "config": {
            "url": webhook_url,
            "content_type": "json",
            "secret": webhook_secret,
        },
    }

    try:
        webhook_response = requests.post(
            f"https://api.github.com/repos/{github_username}/{repo_name}/hooks",
            headers=headers,
            json=payload,
            timeout=5,
        )
        webhook_response.raise_for_status()

        # Store webhook details in the database
        webhook_data = webhook_response.json()
        if webhook_response.status_code == 201:
            # Successfully created webhook, save to database
            Webhook.objects.create(
                user=user,
                repository=f"{github_username}/{repo_name}",
                webhook_id=webhook_data.get("id"),
                stack=stack,
                secret=webhook_secret,
            )
        else:
            # Handle unexpected response
            return JsonResponse({"error": "Failed to create webhook"}, status=400)
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Failed to create webhook: {str(e)}"}, status=400
        )

    return JsonResponse(
        {"message": "Webhook created successfully", "webhook_secret": webhook_secret},
        status=201,
    )


def github_webhook(request: HttpRequest) -> JsonResponse:
    """Handles GitHub webhook events."""

    ALLOWED_EVENTS = {"push"}

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    response = assertRequiredFields(
        request, ["X-Hub-Signature-256", "X-GitHub-Hook-ID"], "header"
    )
    if isinstance(response, JsonResponse):
        return response

    signature, webhook_id = response

    response = assertRequiredFields(
        request, ["X-GitHub-Event", "repository", "ref", "payload"], "header"
    )
    if isinstance(response, JsonResponse):
        return response

    event_type, repository_name, ref, payload = response

    webhook = get_object_or_404(Webhook, webhook_id=webhook_id)

    computed_signature = (
        "sha256="
        + hmac.new(webhook.secret.encode(), request.body, hashlib.sha256).hexdigest()
    )

    if not hmac.compare_digest(signature, computed_signature):
        return JsonResponse({"error": "Invalid signature"}, status=403)

    # Parse webhook payload
    repository_name = payload.get("repository", {}).get("full_name", "unknown/repo")

    # Check if this involves the main branch
    if not ref or not ref.endswith("/main"):
        return JsonResponse({"message": "Ignored - not main branch"}, status=200)

    # Ignore events that aren't in the allowed list
    if event_type not in ALLOWED_EVENTS:
        return JsonResponse(
            {"message": f"Ignored event type: {event_type}"}, status=200
        )

    # Find user based on webhook repository
    user = webhook.user

    github_token = get_object_or_404(Token, user=user).get_token()

    gcp_wrapper = GCPUtils()

    # TODO: Handle different repository types
    if repository_name == "Deploy-Box/deploy_box":
        # Handle the specific repository
        print("Handling Deploy-Box/deploy_box repository")

        threading.Thread(
            target=gcp_wrapper.post_build_and_deploy,
            args=(webhook.stack.id, webhook.repository, github_token, "Website"),
        ).start()

    elif repository_name == "HamzaKhairy/green_toolkit":
        # Handle the specific repository
        print("Handling HamzaKhairy/green_toolkit repository")

        threading.Thread(
            target=gcp_wrapper.post_build_and_deploy,
            args=(
                webhook.stack.id,
                webhook.repository,
                github_token,
                "deploybox/MERN/backend",
            ),
        ).start()

        threading.Thread(
            target=gcp_wrapper.post_build_and_deploy,
            args=(
                webhook.stack.id,
                webhook.repository,
                github_token,
                "deploybox/MERN/frontend",
            ),
        ).start()

    else:

        threading.Thread(
            target=gcp_wrapper.post_build_and_deploy,
            args=(webhook.stack.id, webhook.repository, github_token, "backend"),
        ).start()

        threading.Thread(
            target=gcp_wrapper.post_build_and_deploy,
            args=(webhook.stack.id, webhook.repository, github_token, "frontend"),
        ).start()

    return JsonResponse({"status": "success", "event_type": event_type}, status=200)
