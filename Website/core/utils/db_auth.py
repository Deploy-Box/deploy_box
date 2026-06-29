"""
Azure Entra ID token provider for PostgreSQL authentication.

Uses DefaultAzureCredential so the same code works:
  - Locally via `az login` (developer Entra identity)
  - In Azure via the app's managed identity
"""

import logging
import threading

from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_AZURE_POSTGRES_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"

_credential = None
_lock = threading.Lock()


def _get_credential() -> DefaultAzureCredential:
    """Lazy-initialise a shared DefaultAzureCredential instance."""
    global _credential
    if _credential is None:
        with _lock:
            if _credential is None:
                _credential = DefaultAzureCredential()
    return _credential


def get_azure_postgres_token() -> str:
    """Return a fresh Entra access token for Azure Database for PostgreSQL."""
    credential = _get_credential()
    token = credential.get_token(_AZURE_POSTGRES_SCOPE)
    return token.token
