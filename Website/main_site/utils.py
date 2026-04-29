import os
import logging
import requests

from core.utils.key_vault_client import KeyVaultClient

logger = logging.getLogger(__name__)


def send_email(to_emails: list[str], subject: str, html_content: str) -> None:
    """Send an email via the Deploy Box APIs email endpoint.

    Follows the same OAuth2 → POST /api/v1/email pattern used
    by the IaC container-app for error notifications.
    """
    api_base_url = os.environ.get(
        "DEPLOY_BOX_API_BASE_URL",
        "https://deploy-box-apis-func-dev.azurewebsites.net",
    ).rstrip("/")

    key_vault = KeyVaultClient()
    client_id = key_vault.get_secret("deploy-box-apis-client-id")
    client_secret = key_vault.get_secret("deploy-box-apis-client-secret")

    if not client_id or not client_secret:
        logger.error("Missing API credentials for email — check Key Vault secrets.")
        raise RuntimeError("Email service credentials are not configured.")

    # Obtain Bearer token
    token_url = f"{api_base_url}/api/client_self_service/oauth2/token"
    token_response = requests.post(
        token_url,
        json={"client_id": client_id, "client_secret": client_secret},
        timeout=30,
    )
    token_response.raise_for_status()
    access_token = token_response.json().get("access_token")

    if not access_token:
        logger.error("OAuth2 token response did not contain an access_token.")
        raise RuntimeError("Failed to obtain access token for email service.")

    # Send the email
    email_url = f"{api_base_url}/api/v1/email"
    email_response = requests.post(
        email_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "to_emails": to_emails,
            "subject": subject,
            "html_content": html_content,
        },
        timeout=30,
    )
    email_response.raise_for_status()
    logger.info("Email sent successfully: %s", subject)
