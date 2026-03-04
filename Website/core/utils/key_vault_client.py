from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class KeyVaultClient:
    """
    A singleton client for retrieving secrets from Azure Key Vault using managed identity authentication.
    Only one instance of this client will be created per process. Secrets are cached in-memory after
    the first retrieval to avoid redundant network calls.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, vault_url: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, vault_url: Optional[str] = None):
        if self._initialized:
            if vault_url and vault_url != self.vault_url:
                logger.warning(
                    "KeyVaultClient is a singleton — ignoring new vault_url %r "
                    "(already configured with %r)",
                    vault_url,
                    self.vault_url,
                )
            return

        self.vault_url = vault_url or self._vault_url_from_env()
        self._cache: dict[str, Optional[str]] = {}
        self._credential_available = False

        logger.info("Initializing Key Vault client for %s", self.vault_url)
        logger.debug(
            "Azure env: KEY_VAULT_NAME=%s, AZURE_CLIENT_ID=%s, AZURE_TENANT_ID=%s",
            os.getenv("KEY_VAULT_NAME"),
            os.getenv("AZURE_CLIENT_ID"),
            os.getenv("AZURE_TENANT_ID"),
        )

        try:
            self.credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)
            self._credential_available = True
            logger.info("Key Vault client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Key Vault client: %s", e, exc_info=True)
            logger.warning(
                "Key Vault unavailable — secrets will fall back to environment variables."
            )
        finally:
            self._initialized = True

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _vault_url_from_env() -> str:
        vault_name = os.getenv("KEY_VAULT_NAME")
        if not vault_name:
            raise ValueError(
                "KEY_VAULT_NAME environment variable is not set and no vault_url provided."
            )
        return f"https://{vault_name}.vault.azure.net/"

    @staticmethod
    def _env_fallback(secret_name: str) -> Optional[str]:
        """Try to resolve a secret from an environment variable (SECRET_NAME convention)."""
        env_var = secret_name.upper().replace("-", "_")
        value = os.getenv(env_var)
        if value:
            logger.info("Using environment variable '%s' as fallback for secret '%s'", env_var, secret_name)
        return value

    # ------------------------------------------------------------------ public

    def get_secret(self, secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret from Key Vault with caching and automatic env-var fallback.

        Lookup order:
        1. In-memory cache
        2. Key Vault (if credentials are available)
        3. Environment variable  (SECRET_NAME convention)
        4. ``default_value``
        5. ``None`` (never raises during Django settings import)
        """
        if not secret_name:
            logger.error("get_secret called with empty secret_name")
            return None

        # 1. Cache hit
        if secret_name in self._cache:
            return self._cache[secret_name]

        # 2. Key Vault
        if self._credential_available:
            try:
                logger.debug("Fetching secret '%s' from Key Vault", secret_name)
                value = self.client.get_secret(secret_name).value
                logger.info("Retrieved secret '%s' from Key Vault", secret_name)
                self._cache[secret_name] = value
                return value
            except Exception as e:
                logger.error("Error retrieving secret '%s': %s", secret_name, e, exc_info=True)

        # 3. Environment variable fallback (always attempted)
        env_value = self._env_fallback(secret_name)
        if env_value is not None:
            self._cache[secret_name] = env_value
            return env_value

        # 4. Explicit default
        if default_value is not None:
            logger.warning("Using default value for secret '%s'", secret_name)
            self._cache[secret_name] = default_value
            return default_value

        # 5. Nothing available — return None so Django settings can still load
        logger.error(
            "No value found for secret '%s' (Key Vault, env var, or default). Returning None.",
            secret_name,
        )
        return None


if __name__ == "__main__":
    kv_client = KeyVaultClient()
    try:
        secret_value = kv_client.get_secret("azure-container-app-environment-id")
        print(f"Retrieved secret value: {secret_value}")
    except Exception as e:
        print(f"Error: {e}")