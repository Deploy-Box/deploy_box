from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
import threading
import logging
import traceback
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

class KeyVaultClient:
    """
    A singleton client for retrieving secrets from Azure Key Vault using managed identity authentication.
    Only one instance of this client will be created per process.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, vault_url: Optional[str] = None):
        """
        Create a new instance only if one doesn't already exist.
        
        Args:
            vault_url (str, optional): The Key Vault URL. If not provided, will be constructed
                                     from environment variables or default naming convention.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(KeyVaultClient, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, vault_url: Optional[str] = None):
        """
        Initialize the Key Vault client only once.
        
        Args:
            vault_url (str, optional): The Key Vault URL. If not provided, will be constructed
                                     from environment variables or default naming convention.
        """
        if self._initialized:
            return
            
        if vault_url:
            self.vault_url = vault_url
        else:
            # Construct vault URL from environment or use default naming convention
            vault_name = os.getenv('KEY_VAULT_NAME')
            if not vault_name:
                raise ValueError("KEY_VAULT_NAME environment variable is not set and no vault_url provided.")
            
            self.vault_url = f"https://{vault_name}.vault.azure.net/"
        
        # Use DefaultAzureCredential which supports managed identity, service principal, etc.
        logger.info(f"Initializing Key Vault client with vault URL: {self.vault_url}")
        logger.info(f"Environment variables: KEY_VAULT_NAME={os.getenv('KEY_VAULT_NAME')}")
        logger.info(f"Environment variables: AZURE_CLIENT_ID={os.getenv('AZURE_CLIENT_ID')}")
        logger.info(f"Environment variables: AZURE_TENANT_ID={os.getenv('AZURE_TENANT_ID')}")
        logger.info(f"Environment variables: AZURE_SUBSCRIPTION_ID={os.getenv('AZURE_SUBSCRIPTION_ID')}")
        
        try:
            # Attempt to create a credential and client. Authentication may fail in CI/local
            # environments where no Azure authentication is available; handle that gracefully.
            self.credential = DefaultAzureCredential()
            logger.info("DefaultAzureCredential initialized successfully")
            self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)
            logger.info("SecretClient initialized successfully")
            self._credential_available = True
            self._initialized = True
        except Exception as e:
            # Don't raise here: make KeyVaultClient resilient so Django can import in CI
            logger.error(f"Failed to initialize Key Vault client: {e}")
            logger.error(f"Key Vault initialization error traceback: {traceback.format_exc()}")
            # Mark credential as unavailable and allow get_secret to use environment fallbacks
            self._credential_available = False
            self._initialized = True
            # If this looks like a network/DNS issue, set a network flag too
            if "getaddrinfo failed" in str(e) or "Failed to resolve" in str(e):
                logger.warning("Network/DNS issue detected during Key Vault initialization.")
                self._network_issue = True
    
    def get_secret(self, secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret from Key Vault.
        
        Args:
            secret_name (str): The name of the secret to retrieve
            default_value (str, optional): Default value to return if secret is not found
            
        Returns:
            str: The secret value or default_value if not found
        """
        # If credentials are not available or we detected network issues, use environment fallback
        if not getattr(self, '_credential_available', True) or getattr(self, '_network_issue', False):
            logger.warning(f"Key Vault credential unavailable or network issue; using environment variable fallback for '{secret_name}'")
            env_var_name = secret_name.upper().replace("-", "_")
            env_value = os.getenv(env_var_name)
            if env_value:
                logger.info(f"Using environment variable '{env_var_name}' as fallback for secret '{secret_name}'")
                return env_value
            elif default_value is not None:
                logger.warning(f"Using default value for secret '{secret_name}'")
                return default_value
            else:
                # Don't raise an exception during Django settings import; return None and let caller decide
                logger.error(f"Key Vault unavailable and no environment variable or default for '{secret_name}'. Returning None.")
                return None
        
        try:
            logger.info(f"Attempting to retrieve secret '{secret_name}' from Key Vault: {self.vault_url}")
            secret = self.client.get_secret(secret_name)
            logger.info(f"Successfully retrieved secret '{secret_name}'")
            return secret.value
        except Exception as e:
            logger.error(f"Error retrieving secret '{secret_name}': {str(e)}")
            logger.error(f"Secret retrieval error traceback: {traceback.format_exc()}")
            
            # Check if this is a network/DNS issue
            if "getaddrinfo failed" in str(e) or "Failed to resolve" in str(e):
                logger.warning(f"Network/DNS issue detected for Key Vault. This is likely a local development environment.")
                logger.warning(f"Attempting to use environment variable fallback for '{secret_name}'")
                
                # Try to get the secret from environment variables as fallback
                env_var_name = secret_name.upper().replace("-", "_")
                env_value = os.getenv(env_var_name)
                if env_value:
                    logger.info(f"Using environment variable '{env_var_name}' as fallback for secret '{secret_name}'")
                    return env_value
            
            if default_value is not None:
                logger.warning(f"Using default value for secret '{secret_name}'")
                return default_value
            raise Exception(f"Failed to retrieve secret '{secret_name}' from Key Vault: {str(e)}")
        
if __name__ == "__main__":
    # Example usage
    kv_client = KeyVaultClient()
    try:
        secret_value = kv_client.get_secret("azure-container-app-environment-id")
        print(f"Retrieved secret value: {secret_value}")
    except Exception as e:
        print(f"Error: {e}")