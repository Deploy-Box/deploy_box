"""
Base settings shared across all environments.
Environment-specific files (dev.py, prod.py) import from here and override as needed.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

from core.utils.key_vault_client import KeyVaultClient

load_dotenv()

_kv = KeyVaultClient()

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
# BASE_DIR points to the Website/ folder (two levels up because settings is now a package)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

HOST = os.getenv("HOST")
if not HOST:
    HOST = "http://localhost"
    print("WARNING: HOST not set, defaulting to", HOST)
print("HOST set to", HOST)

# ──────────────────────────────────────────────
# Security
# ──────────────────────────────────────────────
SECRET_KEY = _kv.get_secret("deploy-box-django-secret-key")
ENV = os.getenv("ENV", "LOCAL").upper()

# WorkOSSessionMiddleware replaces AuthenticationMiddleware; silence the admin check.
SILENCED_SYSTEM_CHECKS = ["admin.E408"]

ALLOWED_HOSTS: list[str] = [
    "deploy-box.com",
    "dev.deploy-box.com",
    "host.docker.internal",
]

ROOT_URLCONF = "core.urls"

# ──────────────────────────────────────────────
# Installed Apps
# ──────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
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
    "marketplace",
    "payments",
    "blogs",
    "deploy_box_apis",
    "taggit",
    "django_ckeditor_5",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.WorkOSSessionAuthentication",
    ]
}

# ──────────────────────────────────────────────
# WorkOS
# ──────────────────────────────────────────────
WORKOS = {
    "CLIENT_ID": os.getenv("WORKOS_CLIENT_ID"),
    "API_KEY": _kv.get_secret("workos-api-key"),
    "REDIRECT_URI": f"{HOST}/api/v1/accounts/oauth/workos/callback",
}

# ──────────────────────────────────────────────
# Sessions & Security  (safe defaults — overridden per env)
# ──────────────────────────────────────────────
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = True
SECURE_SSL_REDIRECT = False # TLS is terminated at the load balancer

CSRF_TRUSTED_ORIGINS: list[str] = []
for host in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.extend([f"https://{host}", f"http://{host}"])

CSRF_COOKIE_SECURE = True
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ──────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ──────────────────────────────────────────────
# Tailwind
# ──────────────────────────────────────────────
TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1"]
NPM_BIN_PATH = os.getenv("NPM_BIN_PATH", "/usr/bin/npm")

# ──────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "core.middleware.WorkOSSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.LoginRequiredMiddleware",
]

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": _kv.get_secret(
            "deploy-box-postgresql-db-password"
        ),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
        "CONN_MAX_AGE": 600,
    }
}

# ──────────────────────────────────────────────
# Static & Media Files
# ──────────────────────────────────────────────
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

# ──────────────────────────────────────────────
# Authentication (all auth flows go through WorkOS)
# ──────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.UserProfile"

# ──────────────────────────────────────────────
# External Services
# ──────────────────────────────────────────────
STRIPE = {
    "PUBLISHABLE_KEY": _kv.get_secret(
        "stripe-publishable-key"
    ),
    "SECRET_KEY": _kv.get_secret(
        "stripe-secret-key"
    ),
    "WEBHOOK_SECRET": _kv.get_secret(
        "stripe-webhook-secret"
    ),
}

GITHUB = {
    "CLIENT_ID": os.environ.get("DEPLOY_BOX_GITHUB_CLIENT_ID"),
    "CLIENT_SECRET": _kv.get_secret("deploy-box-github-client-secret"),
    "TOKEN_KEY": _kv.get_secret("deploy-box-github-token-key"),
}

DEPLOY_BOX_STACK_ENDPOINT = os.getenv("DEPLOY_BOX_STACK_ENDPOINT")
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "dev.deploy-box.com")

AZURE_SERVICE_BUS = {
    "CONNECTION_STRING": os.getenv("AZURE_SERVICE_BUS_CONNECTION_STRING"),
    "QUEUE_NAME": "iac",
}

# ──────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────
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

# Password validation is handled by WorkOS — no Django validators needed.
AUTH_PASSWORD_VALIDATORS = []

# ──────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────
# CKEditor 5
# ──────────────────────────────────────────────
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": {
            "items": [
                "heading",
                "|",
                "bold",
                "italic",
                "link",
                "bulletedList",
                "numberedList",
                "blockQuote",
                "imageUpload",
            ],
        },
    },
    "extends": {
        "blockToolbar": [
            "paragraph",
            "heading1",
            "heading2",
            "heading3",
            "|",
            "bulletedList",
            "numberedList",
            "|",
            "blockQuote",
        ],
        "toolbar": {
            "items": [
                "heading",
                "|",
                "outdent",
                "indent",
                "|",
                "bold",
                "italic",
                "link",
                "underline",
                "strikethrough",
                "code",
                "subscript",
                "superscript",
                "highlight",
                "|",
                "codeBlock",
                "sourceEditing",
                "insertImage",
                "bulletedList",
                "numberedList",
                "todoList",
                "|",
                "blockQuote",
                "imageUpload",
                "|",
                "fontSize",
                "fontFamily",
                "fontColor",
                "fontBackgroundColor",
                "mediaEmbed",
                "removeFormat",
                "insertTable",
            ],
            "shouldNotGroupWhenFull": "true",
        },
        "image": {
            "toolbar": [
                "imageTextAlternative",
                "|",
                "imageStyle:alignLeft",
                "imageStyle:alignRight",
                "imageStyle:alignCenter",
                "imageStyle:side",
                "|",
            ],
            "styles": [
                "full",
                "side",
                "alignLeft",
                "alignRight",
                "alignCenter",
            ],
        },
        "heading": {
            "options": [
                {
                    "model": "paragraph",
                    "title": "Paragraph",
                    "class": "ck-heading_paragraph",
                },
                {
                    "model": "heading1",
                    "view": "h1",
                    "title": "Heading 1",
                    "class": "ck-heading_heading1",
                },
                {
                    "model": "heading2",
                    "view": "h2",
                    "title": "Heading 2",
                    "class": "ck-heading_heading2",
                },
                {
                    "model": "heading3",
                    "view": "h3",
                    "title": "Heading 3",
                    "class": "ck-heading_heading3",
                },
            ]
        },
    },
    "list": {
        "properties": {
            "styles": "true",
            "startIndex": "true",
            "reversed": "true",
        }
    },
}
