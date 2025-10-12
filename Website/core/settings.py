from pathlib import Path
from dotenv import load_dotenv
import os

from core.utils.config_loader import load_config
from core.utils.key_vault_client import KeyVaultClient

load_dotenv()
load_config()

BASE_DIR = Path(__file__).resolve().parent.parent

HOST = os.environ.get("HOST")
assert HOST is not None, "HOST env must be set"

# SECURITY
SECRET_KEY = KeyVaultClient().get_secret('deploy-box-django-secret-key', os.getenv("DJANGO_SECRET_KEY"))
ENV = os.environ.get("ENV", "LOCAL").upper()
# DEBUG = ENV == "DEV" or ENV == "LOCAL"
DEBUG = True # TODO: remove eventually

ALLOWED_HOSTS = [
    "deploy-box.onrender.com",
    "deploy-box.kalebwbishop.com",
    "deploy-box.com",
    "dev.deploy-box.com",
    "https://b93437058b73.ngrok-free.app"
]
if DEBUG:
    ALLOWED_HOSTS.extend(
        [
            "127.0.0.1",
            "localhost",
            "c361-152-117-84-230.ngrok-free.app",
            HOST.replace("https://", "").replace("http://", ""),
        ]
    )

ROOT_URLCONF = "core.urls"

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "oauth2_provider",
    "tailwind",
    "theme",
    "rest_framework",
    # Custom Apps
    "main_site",
    "accounts",
    "github",
    "stacks",
    "projects",
    "organizations",
    "payments",
    "blogs",
    "taggit", # for tagging in blogs
    "django_ckeditor_5",  # for rich text editor in blogs to handle content like images, links, etc.
]

if DEBUG:
    INSTALLED_APPS.extend(
        [
            "django_browser_reload",
            "django_extensions",
        ]
    )

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",  # Or OAuth2
    ]
}


# Authentication
OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,  # 1 hour
    "REFRESH_TOKEN_EXPIRE_SECONDS": 86400,  # 1 day
    "ROTATE_REFRESH_TOKENS": True,
    "GRANT_TYPES": [
        "password",
        "client_credentials",
    ],
    "SCOPES": {
        "read": "Read scope",
        "write": "Write scope",
        "m2m": "Machine to machine scope",
    },
}

OAUTH2_PASSWORD_CREDENTIALS = {
    "client_id": os.environ.get("OAUTH2_PASSWORD_CREDENTIALS_CLIENT_ID"),
    "client_secret": os.environ.get("OAUTH2_PASSWORD_CREDENTIALS_CLIENT_SECRET"),
    "redirect_uri": f"{HOST}/callback/",
    "token_url": f"{HOST}/o/token/",
}

OAUTH2_CLIENT_CREDENTIALS = {
    "client_id": os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_ID"),
    "client_secret": os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_SECRET"),
    "token_url": f"{HOST}/o/token/",
}

# Sessions & Security
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = True

# Disable CSRF protection
CSRF_TRUSTED_ORIGINS: list[str] = []

for host in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.extend([f"https://{host}", f"http://{host}"])

CSRF_COOKIE_SECURE = not DEBUG
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False

SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = not DEBUG

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# Tailwind
TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1"]
NPM_BIN_PATH = os.environ.get("NPM_BIN_PATH", "/usr/bin/npm")

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Database
def get_db_password():
    """
    Get database password from Key Vault with environment variable fallback.
    This provides a robust fallback mechanism for local development.
    """
    # First prefer explicit CI / deployment environment variable (if set)
    env_password = os.environ.get("DEPLOY_BOX_POSTGRESQL_DB_PASSWORD") or os.environ.get("DB_PASSWORD")
    if env_password:
        # Provide visibility in CI logs that an env var was used instead of Key Vault
        print("Info: Using environment variable for database password (DEPLOY_BOX_POSTGRESQL_DB_PASSWORD or DB_PASSWORD)")
        return env_password

    # Next, fall back to Key Vault if available (with KeyVaultClient handling its own fallbacks)
    try:
        kv_password = KeyVaultClient().get_secret("deploy-box-postgresql-db-password")
        if kv_password:
            return kv_password
        # if KeyVaultClient returned None, treat as missing and continue to final error
    except Exception as e:
        # Don't crash immediately here; we'll raise a clearer error below if nothing found
        print(f"Warning: Key Vault access failed while retrieving DB password: {e}")

    # If we reached here, no password was found
    raise Exception("Database password not available: please set DEPLOY_BOX_POSTGRESQL_DB_PASSWORD or DB_PASSWORD in the environment, or ensure Key Vault access is configured")

DATABASES = {
    # "default": {
    #     "ENGINE": "django.db.backends.sqlite3",
    #     "NAME": BASE_DIR / 'db.sqlite3',
    # }
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": get_db_password(),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
        # "OPTIONS": {
        #     "sslrootcert": os.environ.get("DB_SSL_CERT"),
        # },
        "CONN_MAX_AGE": 600,
    }
}

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# Static & Media Files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "theme" / "static",
    BASE_DIR / "main_site" / "static",
    BASE_DIR / "blogs" / "static",
]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "main_site", "media")

# Authentication Redirects
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

#  External Services
STRIPE = {
    "PUBLISHABLE_KEY": KeyVaultClient().get_secret("stripe-publishable-key"),
    "SECRET_KEY": KeyVaultClient().get_secret("stripe-secret-key"),
    # Prefer Key Vault, fall back to STRIPE_WEBHOOK_SECRET env var if Key Vault unavailable
    "WEBHOOK_SECRET": KeyVaultClient().get_secret("stripe-webhook-secret", os.environ.get("STRIPE_WEBHOOK_SECRET")),
}

GITHUB = {
    "CLIENT_ID": os.environ.get("DEPLOY_BOX_GITHUB_CLIENT_ID"),
    "CLIENT_SECRET": KeyVaultClient().get_secret('deploy-box-github-client-secret'),
    "TOKEN_KEY": KeyVaultClient().get_secret("deploy-box-github-token-key"),
}

AZURE = {
    "CLIENT_ID": KeyVaultClient().get_secret("arm-client-id"),
    "CLIENT_SECRET": KeyVaultClient().get_secret("arm-client-secret"), 
    "TENANT_ID": KeyVaultClient().get_secret("arm-tenant-id"),
    "STORAGE_CONNECTION_STRING": KeyVaultClient().get_secret("azure-storage-connection-string"),
    "CONTAINER_NAME": KeyVaultClient().get_secret("container-name"),
    # "RESOURCE_GROUP_NAME": KeyVaultClient().get_secret("resource-group-name"),
    "ACR_PASSWORD": KeyVaultClient().get_secret("acr-password"),
}

# DeployBox Stack Endpoint for file downloads
# This environment variable should point to a base URL where stack source files are hosted
# The system will append /{stack_id}/source.zip to this URL when downloading files
# Example: DEPLOY_BOX_STACK_ENDPOINT=https://api.deploybox.com/stacks
DEPLOY_BOX_STACK_ENDPOINT = os.environ.get("DEPLOY_BOX_STACK_ENDPOINT")

# Templates Configuration
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "accounts.UserProfile"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': {
            'items': ['heading', '|', 'bold', 'italic', 'link',
                      'bulletedList', 'numberedList', 'blockQuote', 'imageUpload', ],
                    },
    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': {
            'items': ['heading', '|', 'outdent', 'indent', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
                      'code','subscript', 'superscript', 'highlight', '|', 'codeBlock', 'sourceEditing', 'insertImage',
                    'bulletedList', 'numberedList', 'todoList', '|',  'blockQuote', 'imageUpload', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'mediaEmbed', 'removeFormat',
                    'insertTable',
                    ],
            'shouldNotGroupWhenFull': 'true'
        },
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side',  '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]

        },
        'heading' : {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        }
    },
    'list': {
        'properties': {
            'styles': 'true',
            'startIndex': 'true',
            'reversed': 'true',
        }
    }
}
