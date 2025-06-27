import requests
import hmac
import hashlib
import secrets
import threading
import json
import logging
from cryptography.fernet import Fernet
from typing import cast

from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string

import stacks.services as stack_services
from core.decorators import oauth_required, AuthHttpRequest
from core.helpers import request_helpers
from github.models import Webhook, Token
from stacks.models import Stack
from core.utils.DeployBoxIAC.main import DeployBoxIAC

# from stacks.services import get_stack
from accounts.models import UserProfile

# GitHub OAuth credentials
CLIENT_ID = settings.GITHUB.get("CLIENT_ID")
CLIENT_SECRET = settings.GITHUB.get("CLIENT_SECRET")
GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPOS_URL = "https://api.github.com/user/repos"

logger = logging.getLogger(__name__)


@oauth_required()
def login(request: AuthHttpRequest) -> HttpResponse:
    """Redirects users to GitHub OAuth page."""
    next_url = request.GET.get("next", "")

    # Create a unique state token that includes user ID and next URL
    ENCRYPTION_KEY = settings.GITHUB["TOKEN_KEY"]

    if not ENCRYPTION_KEY:
        raise ValueError("GITHUB_TOKEN_KEY is not set")

    state_data = {"user_id": str(request.auth_user.pk), "next": next_url}
    cipher = Fernet(ENCRYPTION_KEY)
    state = cipher.encrypt(json.dumps(state_data).encode())

    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    return redirect(f"{GITHUB_AUTH_URL}?client_id={CLIENT_ID}&scope=repo&state={state}")


def callback(request: HttpRequest) -> HttpResponse:
    """Handles GitHub OAuth callback and fetches user info."""
    code = request.GET.get("code")
    state = request.GET.get(
        "state", ""
    )  # Get the state parameter which contains our next URL

    if not state:
        return HttpResponse("No state parameter provided", status=400)

    ENCRYPTION_KEY = settings.GITHUB["TOKEN_KEY"]

    if not ENCRYPTION_KEY:
        raise ValueError("GITHUB_TOKEN_KEY is not set")

    cipher = Fernet(ENCRYPTION_KEY)

    # Clean up the state parameter by removing b' prefix and single quotes if present
    if state.startswith("b'") and state.endswith("'"):
        state = state[2:-1]

    try:
        state_data = json.loads(cipher.decrypt(state.encode()).decode())
    except Exception as e:
        logger.error(f"Failed to decrypt state: {str(e)}")
        return HttpResponse("Invalid state parameter", status=400)

    if not code:
        return HttpResponse("Authorization failed", status=400)

    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"

    # Exchange code for access token
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code},
    )
    token_json = token_response.json()

    print(token_json)
    access_token = token_json.get("access_token")

    if not access_token:
        return HttpResponse("Failed to retrieve access token", status=400)

    # Fetch user info from GitHub API
    GITHUB_USER_URL = "https://api.github.com/user"
    user_response = requests.get(
        GITHUB_USER_URL, headers={"Authorization": f"token {access_token}"}
    )
    user_data = user_response.json()

    if "id" not in user_data:
        return HttpResponse("Failed to retrieve user info", status=400)

    # Check if user already has a token
    user = UserProfile.objects.get(id=state_data["user_id"])

    # Check if user already has a token
    github_token, _ = Token.objects.get_or_create(user=user)
    github_token.set_token(access_token)
    github_token.save()

    # Store user info in session
    request.session["github_user"] = user_data
    request.session.modified = True

    print("access_token:", access_token)  # For debugging purposes, remove in production

    # Use the state parameter as the return URL
    if state_data["next"]:
        return redirect(state_data["next"])

    return redirect(reverse("main_site:dashboard"))


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


@oauth_required()
def list_repos(request: AuthHttpRequest) -> HttpResponse:
    """Fetch and display user repositories with a deploy button."""
    user = request.auth_user
    github_token = get_object_or_404(Token, user=user).get_token()

    repo_response = requests.get(
        GITHUB_REPOS_URL,
        headers={"Authorization": f"token {github_token}"},
        params={"per_page": 100},
    )

    if repo_response.status_code != 200:
        return JsonResponse({"error": "Failed to fetch repositories"}, status=400)

    repos = repo_response.json()

    # Fetch user stacks
    stacks = stack_services.get_stacks(user)

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


def create_iac_webhook(
    repo_url: str, stack: Stack, directory: str, github_token: str
):
    
    full_repo_url = f"https://github.com/{repo_url}.git#main"

    return {
        "task": {
            "type": "Docker",
            "dockerFilePath": "Dockerfile",
            "contextPath": full_repo_url,
            "contextDirectory": directory,
            "contextAccessToken": github_token,
            "imageNames": [f"{stack.id}{directory}:latest"]
        },
    }


@oauth_required()
def create_github_webhook(request: HttpRequest) -> JsonResponse:
    """Create and store a GitHub webhook for a user's repository."""
    user = cast(UserProfile, request.user)
    logger.info(f"Starting webhook creation process for user {user.username}")

    try:
        repo_name, stack_id = request_helpers.assertRequestFields(
            request, ["repo-name", "stack-id"]
        )
        logger.info(
            f"Received webhook creation request for repository {repo_name} and stack {stack_id}"
        )
    except request_helpers.MissingFieldError as e:
        logger.error(f"Missing required fields in webhook creation request: {str(e)}")
        return e.to_response()

    stack = Stack.objects.get(pk=stack_id)
    github_token = get_object_or_404(Token, user=user).get_token()

    headers = {"Authorization": f"token {github_token}"}
    try:
        logger.debug("Verifying GitHub token validity")
        response = requests.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=5)
        response.raise_for_status()
        logger.debug("GitHub token verification successful")
    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {str(e)}")
        return JsonResponse(
            {"error": f"GitHub API request failed: {str(e)}"}, status=400
        )

    # Split repository name and validate format
    try:
        owner, repo = repo_name.split("/")
        if not owner or not repo:
            raise ValueError("Invalid repository format")
        logger.debug(f"Repository format validated: owner={owner}, repo={repo}")
    except ValueError as e:
        logger.error(f"Invalid repository format: {repo_name}")
        return JsonResponse(
            {"error": "Invalid repository format. Expected format: owner/repo"},
            status=400,
        )

    # Verify repository existence and access
    repo_check_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    try:
        logger.debug(f"Verifying repository existence: {repo_check_url}")
        repo_response = requests.get(repo_check_url, headers=headers, timeout=5)
        if repo_response.status_code == 404:
            logger.error(f"Repository not found: {repo_name}")
            return JsonResponse(
                {"error": "Repository not found or you don't have access to it"},
                status=404,
            )
        repo_response.raise_for_status()
        logger.debug(f"Repository verification successful: {repo_name}")
    except requests.RequestException as e:
        logger.error(f"Failed to verify repository {repo_name}: {str(e)}")
        return JsonResponse(
            {"error": f"Failed to verify repository: {str(e)}"}, status=400
        )

    # Generate a unique webhook secret
    webhook_secret = secrets.token_hex(32)
    logger.debug("Generated webhook secret")

    # Webhook URL
    webhook_url = f"{settings.HOST}/api/v1/github/webhook/"

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
        logger.info(f"Creating webhook for repository {repo_name}")
        webhook_response = requests.post(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/hooks",
            headers=headers,
            json=payload,
            timeout=5,
        )

        if webhook_response.status_code == 404:
            logger.error(
                f"Failed to create webhook for {repo_name}: Repository not found or insufficient permissions"
            )
            return JsonResponse(
                {
                    "error": "Repository not found or you don't have permission to create webhooks"
                },
                status=404,
            )
        elif webhook_response.status_code == 422:
            error_details = webhook_response.json()
            logger.error(
                f"Failed to create webhook for {repo_name}: Validation error. Details: {error_details}"
            )
            return JsonResponse(
                {
                    "error": "Failed to create webhook: Validation error",
                    "details": error_details,
                },
                status=422,
            )
        webhook_response.raise_for_status()

        # Store webhook details in the database
        webhook_data = webhook_response.json()
        logger.debug(
            f"Webhook created successfully, storing in database: {webhook_data.get('id')}"
        )
        Webhook.objects.create(
            user=user,
            repository=f"{owner}/{repo}",
            webhook_id=webhook_data.get("id"),
            stack=stack,
            secret=webhook_secret,
        )

        iac = stack.iac

        if stack.purchased_stack.type == "MERN":
            iac["azurerm_container_app"][f"mern-backend-{stack.id}"]["template"]["container"][0].update({"image": create_iac_webhook(f"{owner}/{repo}", stack, "backend", github_token)})
            iac["azurerm_container_app"][f"mern-frontend-{stack.id}"]["template"]["container"][0].update({"image": create_iac_webhook(f"{owner}/{repo}", stack, "frontend", github_token)})
        elif stack.purchased_stack.type == "Django":
            iac["azurerm_container_app"][f"django-{stack.id}"]["template"]["container"][0].update({"image": create_iac_webhook(f"{owner}/{repo}", stack, "backend", github_token)})
        else:
            pass

        stack.iac = iac
        print(json.dumps(stack.iac, indent=2))
        stack.save()

        logger.info(
            f"Webhook successfully created and stored for repository {repo_name}"
        )



    except requests.RequestException as e:
        error_message = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_details = e.response.json()
                logger.error(
                    f"Failed to create webhook for {repo_name}: {error_message}. Response: {error_details}"
                )
                return JsonResponse(
                    {
                        "error": f"Failed to create webhook: {error_message}",
                        "details": error_details,
                    },
                    status=e.response.status_code,
                )
            except ValueError:
                logger.error(
                    f"Failed to create webhook for {repo_name}: {error_message}"
                )
        else:
            logger.error(f"Failed to create webhook for {repo_name}: {error_message}")
        return JsonResponse(
            {"error": f"Failed to create webhook: {error_message}"}, status=400
        )

    return JsonResponse(
        {"message": "Webhook created successfully", "webhook_secret": webhook_secret},
        status=201,
    )


def github_webhook(request: HttpRequest) -> JsonResponse:
    """Handles GitHub webhook events."""

    ALLOWED_EVENTS = {"ping", "push", "pull_request"}

    if request.method != "POST":
        print("Invalid request")
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        signature, webhook_id, event_type = request_helpers.assertRequestFields(
            request,
            ["X-Hub-Signature-256", "X-Github-Hook-Id", "X-Github-Event"],
            body_or_header="header",
        )

    except request_helpers.MissingFieldError as e:
        return e.to_response()

    webhook = get_object_or_404(Webhook, webhook_id=webhook_id)

    computed_signature = (
        "sha256="
        + hmac.new(webhook.secret.encode(), request.body, hashlib.sha256).hexdigest()
    )

    if not hmac.compare_digest(signature, computed_signature):
        return JsonResponse({"error": "Invalid signature"}, status=403)

    # Parse webhook payload
    try:
        payload = json.loads(request.body)
        repository_name = payload.get("repository", {}).get("full_name", "unknown/repo")
        ref = payload.get("ref", "")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    # Check if this involves the main branch
    if not ref or not ref.endswith("/main"):
        if event_type != "ping":
            return JsonResponse({"message": "Ignored - not main branch"}, status=200)

    # Ignore events that aren't in the allowed list
    if event_type not in ALLOWED_EVENTS:
        return JsonResponse(
            {"message": f"Ignored event type: {event_type}"}, status=200
        )

    # Find user based on webhook repository
    user = webhook.user

    deploy_box_iac = DeployBoxIAC()
    print(webhook.stack.iac)
    deploy_box_iac.deploy(f"{webhook.stack.id}-rg", webhook.stack.iac)

    return JsonResponse({"status": "success", "event_type": event_type}, status=200)


@oauth_required()
def get_repos_json(request: AuthHttpRequest) -> JsonResponse:
    """Fetch user repositories and return as JSON."""
    user = request.auth_user
    github_token = get_object_or_404(Token, user=user).get_token()

    repo_response = requests.get(
        GITHUB_REPOS_URL,
        headers={"Authorization": f"token {github_token}"},
        params={"per_page": 100},
    )

    if repo_response.status_code != 200:
        return JsonResponse({"error": "Failed to fetch repositories"}, status=400)

    repos = repo_response.json()
    return JsonResponse({"repositories": repos})
