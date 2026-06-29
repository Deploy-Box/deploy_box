"""
Accounts service layer — business logic for user signup, profile, and auth.

Returns plain data (dicts) or raises ServiceError exceptions.
Never imports Response, JsonResponse, or HttpResponse.
"""
import logging
from django.conf import settings
from django.db import transaction
from workos import WorkOSClient

from accounts.models import UserProfile
from organizations.models import PendingInvites, OrganizationMember, Organization

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(ServiceError):
    def __init__(self, message="Not found"):
        super().__init__(message, status_code=404)


class ValidationError(ServiceError):
    def __init__(self, message="Invalid input"):
        super().__init__(message, status_code=400)


# ── Profile ──────────────────────────────────────────────────────────────────

def get_profile(user: UserProfile) -> dict:
    """Return serializable profile data for the authenticated user."""
    return {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def update_profile(user: UserProfile, data: dict) -> dict:
    """
    Update user profile fields (username, email).
    Raises ValidationError if username/email is already taken.
    """
    username = data.get("username")
    email = data.get("email")

    if username and username != user.username:
        if UserProfile.objects.filter(username=username).exclude(id=user.id).exists():
            raise ValidationError("Username is already taken")
        user.username = username

    if email and email != user.email:
        if UserProfile.objects.filter(email=email).exclude(id=user.id).exists():
            raise ValidationError("Email is already taken")
        user.email = email

    user.save()
    return {"message": "Profile updated successfully"}


def delete_account(user: UserProfile, session) -> dict:
    """Delete a user account after flushing the session."""
    session.flush()
    user.delete()
    return {"message": "Account deleted successfully"}


# ── Signup ───────────────────────────────────────────────────────────────────

def _process_pending_invite(user: UserProfile) -> dict | None:
    """Check for pending org invites by email and auto-join if found."""
    invite = PendingInvites.objects.filter(email=user.email).first()
    if not invite:
        return None

    organization = invite.organization
    OrganizationMember.objects.create(
        user=user, organization=organization, role="member"
    )
    invite.delete()
    return {"organization_id": str(organization.id)}


@transaction.atomic
def signup_regular(validated_data: dict, save_fn) -> dict:
    """
    Regular signup flow.
    save_fn: callable that creates and returns a UserProfile (e.g. serializer.save()).
    """
    user = save_fn()

    try:
        invite_result = _process_pending_invite(user)
    except Exception as e:
        logger.error(f"Error processing pending invite: {e}")
        raise ServiceError("Error processing invitation", status_code=500)

    result = {
        "message": "User created successfully",
        "user_id": str(user.id),
    }
    if invite_result:
        result["message"] = "User created and added to organization successfully"
        result["organization_id"] = invite_result["organization_id"]

    return result


@transaction.atomic
def signup_with_invite(validated_data: dict, save_fn, invite_id: str) -> dict:
    """Signup with an existing organization invite."""
    try:
        pending_invite = PendingInvites.objects.get(id=invite_id)
    except PendingInvites.DoesNotExist:
        raise ValidationError("Invalid or expired invite link")

    if validated_data.get("email") != pending_invite.email:
        raise ValidationError("Email must match the invited email address")

    user = save_fn()

    OrganizationMember.objects.create(
        organization=pending_invite.organization,
        user=user,
        role="member",
    )
    pending_invite.delete()

    return {
        "message": "User created and added to organization successfully",
        "user_id": str(user.id),
        "organization_id": str(pending_invite.organization.id),
    }


@transaction.atomic
def signup_with_transfer(validated_data: dict, save_fn, invite_id: str, transfer_id: str) -> dict:
    """Signup with both organization invite and project transfer."""
    from organizations.models import ProjectTransferInvitation

    try:
        pending_invite = PendingInvites.objects.get(id=invite_id)
    except PendingInvites.DoesNotExist:
        raise ValidationError("Invalid or expired invite link")

    try:
        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id, status="pending")
    except ProjectTransferInvitation.DoesNotExist:
        raise ValidationError("Invalid or expired transfer invitation")

    email = validated_data.get("email")
    if email != pending_invite.email or email != transfer_invitation.to_email:
        raise ValidationError("Email must match the invited email address")

    user = save_fn()

    OrganizationMember.objects.create(
        organization=pending_invite.organization,
        user=user,
        role="member",
    )
    pending_invite.delete()

    # Accept the project transfer
    from organizations.services import accept_project_transfer
    transfer_result = accept_project_transfer(transfer_id, user)

    transfer_completed = getattr(transfer_result, "status_code", None) == 200

    result = {
        "user_id": str(user.id),
        "organization_id": str(pending_invite.organization.id),
        "transfer_completed": transfer_completed,
    }

    if transfer_completed:
        result["message"] = "Account created, organization joined, and project transfer completed successfully"
    else:
        result["message"] = "Account created and organization joined, but project transfer failed. Please contact support."

    return result


# ── WorkOS Auth ──────────────────────────────────────────────────────────────

def workos_authenticate(code: str) -> dict:
    """Exchange a WorkOS authorization code for user profile data."""
    if not code:
        raise ValidationError("Authorization code not provided")

    workos_client = WorkOSClient(
        api_key=settings.WORKOS["API_KEY"],
        client_id=settings.WORKOS["CLIENT_ID"],
    )

    auth_response = workos_client.user_management.authenticate_with_code(
        code=code,
        session=None,
    )

    workos_user = auth_response.user
    email = workos_user.email
    if not email:
        raise ServiceError("Email not available from WorkOS")

    return {
        "workos_user_id": workos_user.id,
        "email": email,
        "first_name": workos_user.first_name or "",
        "last_name": workos_user.last_name or "",
        "access_token": auth_response.access_token,
    }


def get_or_create_workos_user(workos_data: dict) -> UserProfile:
    """Get or create a local UserProfile from WorkOS auth data."""
    workos_user_id = workos_data["workos_user_id"]
    email = workos_data["email"]

    # Try matching by workos_user_id first
    user = UserProfile.objects.filter(workos_user_id=workos_user_id).first()

    if not user:
        # Try matching by email
        user = UserProfile.objects.filter(email=email).first()
        if user:
            user.workos_user_id = workos_user_id
            user.auth_provider = "workos"
            user.save(update_fields=["workos_user_id", "auth_provider"])
            logger.info(f"Linked existing user {user.username} to WorkOS ID {workos_user_id}")

    if not user:
        # Create new user
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while UserProfile.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = UserProfile.objects.create_user(
            username=username,
            email=email,
            first_name=workos_data["first_name"],
            last_name=workos_data["last_name"],
            workos_user_id=workos_user_id,
            auth_provider="workos",
        )
        user.set_unusable_password()
        user.save()
        logger.info(f"Created new user {username} via WorkOS")

        # Auto-join pending org invites
        try:
            _process_pending_invite(user)
        except Exception as inv_err:
            logger.error(f"Error processing pending invite for WorkOS user: {inv_err}")

    return user


def extract_workos_session_id(access_token: str) -> str | None:
    """Decode the WorkOS access token JWT to extract the session ID."""
    try:
        import jwt as pyjwt
        decoded = pyjwt.decode(access_token, options={"verify_signature": False})
        return decoded.get("sid")
    except Exception as jwt_err:
        logger.warning(f"Could not decode WorkOS access_token JWT: {jwt_err}")
        return None


def get_workos_logout_url(workos_session_id: str | None) -> str | None:
    """Build a WorkOS logout URL if session ID is available."""
    if not workos_session_id:
        return None

    try:
        workos_client = WorkOSClient(
            api_key=settings.WORKOS["API_KEY"],
            client_id=settings.WORKOS["CLIENT_ID"],
        )
        return workos_client.user_management.get_logout_url(
            session_id=workos_session_id,
            return_to=settings.HOST,
        )
    except Exception as e:
        logger.warning(f"Failed to build WorkOS logout URL: {e}")
        return None
