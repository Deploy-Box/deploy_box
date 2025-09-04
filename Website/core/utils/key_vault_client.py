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
            vault_name = os.getenv('key-vault-name', 'deploy-box-shared-kv-dev')
            self.vault_url = f"https://{vault_name}.vault.azure.net/"
        
        # Use DefaultAzureCredential which supports managed identity, service principal, etc.
        logger.info(f"Initializing Key Vault client with vault URL: {self.vault_url}")
        logger.info(f"Environment variables: KEY_VAULT_NAME={os.getenv('KEY_VAULT_NAME')}")
        logger.info(f"Environment variables: AZURE_CLIENT_ID={os.getenv('AZURE_CLIENT_ID')}")
        logger.info(f"Environment variables: AZURE_TENANT_ID={os.getenv('AZURE_TENANT_ID')}")
        logger.info(f"Environment variables: AZURE_SUBSCRIPTION_ID={os.getenv('AZURE_SUBSCRIPTION_ID')}")
        
        try:
            self.credential = DefaultAzureCredential()
            logger.info("DefaultAzureCredential initialized successfully")
            self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)
            logger.info("SecretClient initialized successfully")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Key Vault client: {e}")
            logger.error(f"Key Vault initialization error traceback: {traceback.format_exc()}")
            raise
    
    def get_secret(self, secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret from Key Vault.
        
        Args:
            secret_name (str): The name of the secret to retrieve
            default_value (str, optional): Default value to return if secret is not found
            
        Returns:
            str: The secret value or default_value if not found
        """
        try:
            logger.info(f"Attempting to retrieve secret '{secret_name}' from Key Vault: {self.vault_url}")
            secret = self.client.get_secret(secret_name)
            logger.info(f"Successfully retrieved secret '{secret_name}'")
            return secret.value
        except Exception as e:
            logger.error(f"Error retrieving secret '{secret_name}': {str(e)}")
            logger.error(f"Secret retrieval error traceback: {traceback.format_exc()}")
            if default_value is not None:
                logger.warning(f"Using default value for secret '{secret_name}'")
                return default_value
            raise Exception(f"Failed to retrieve secret '{secret_name}' from Key Vault: {str(e)}")