import hmac
import hashlib
import json
import logging

from rest_framework.exceptions import AuthenticationFailed
from core.utils.key_vault_client import KeyVaultClient

logger = logging.getLogger(__name__)

_kv = KeyVaultClient()

IAC_WEBHOOK_SECRET_NAME = "iac-webhook-secret"


def verify_iac_webhook_signature(request) -> None:
    """
    Verify the HMAC-SHA256 signature on an inbound IaC webhook request.

    Raises ``AuthenticationFailed`` if the signature is missing or invalid.
    """
    signature = request.META.get("HTTP_X_WEBHOOK_SIGNATURE_256")
    if not signature:
        logger.warning("IaC webhook request missing X-Webhook-Signature-256 header")
        raise AuthenticationFailed("Missing webhook signature")

    secret = _kv.get_secret(IAC_WEBHOOK_SECRET_NAME)
    if not secret:
        logger.error(
            "Cannot verify IaC webhook — secret '%s' is not configured",
            IAC_WEBHOOK_SECRET_NAME,
        )
        raise AuthenticationFailed("Webhook authentication not configured")

    # Re-serialize the parsed body with the same canonical form used by the sender
    body = json.dumps(request.data, separators=(",", ":"), sort_keys=True).encode()

    computed = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, computed):
        logger.warning("IaC webhook signature mismatch")
        raise AuthenticationFailed("Invalid webhook signature")
