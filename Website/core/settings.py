from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

HOST = os.environ.get("HOST")

# SECURITY
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("ENV", "dev") == "dev"

ALLOWED_HOSTS = [
    "deploy-box.onrender.com",
    "deploy-box.kalebwbishop.com",
]
if DEBUG:
    ALLOWED_HOSTS += [
        "127.0.0.1",
    ]

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
    "rest_framework",
    "rest_framework_simplejwt",
    "oauth2_provider",
    "tailwind",
    "theme",
    "payments.apps.PaymentsConfig",
    "main_site",
    "api",
    "accounts",
    "github",
]

if DEBUG:
    INSTALLED_APPS += [
        "django_browser_reload",
        "django_extensions",
    ]

# Authentication
# REST_FRAMEWORK = {
#     "DEFAULT_AUTHENTICATION_CLASSES": [
#         "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
#     ],
#     "DEFAULT_PERMISSION_CLASSES": [
#         "rest_framework.permissions.IsAuthenticated",
#     ],
# }

OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 36000,
    "AUTHORIZATION_CODE_EXPIRATION": 600,
}

OAUTH2_AUTHORIZATION_CODE = {
    "client_id": os.environ.get("OAUTH2_AUTHORIZATION_CODE_CLIENT_ID"),
    "client_secret": os.environ.get("OAUTH2_AUTHORIZATION_CODE_CLIENT_SECRET"),
    "redirect_uri": f"{HOST}/accounts/callback/",
    "token_url": f"{HOST}/accounts/o/token/",
}

OAUTH2_CLIENT_CREDENTIALS = {
    "client_id": os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_ID"),
    "client_secret": os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_SECRET"),
    "token_url": f"{HOST}/accounts/o/token/",
}

# Sessions & Security
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = True

SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "true").lower() == "true"
CSRF_COOKIE_SECURE = not DEBUG

# Tailwind
TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1"]
NPM_BIN_PATH = os.environ.get("NPM_BIN_PATH", "/usr/bin/npm")

CSRF_TRUSTED_ORIGINS = [
    "https://deploy-box.onrender.com",
    "https://deploy-box.kalebwbishop.com",
]

if DEBUG:
    CSRF_TRUSTED_ORIGINS += [
        "http://12.0.0.1:8000",
    ]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
        "OPTIONS": {
            "sslrootcert": os.environ.get("DB_SSL_CERT"),
        },
        "CONN_MAX_AGE": 600,
    }
}

# Static & Media Files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    BASE_DIR / "theme" / "static",
    BASE_DIR / "main_site" / "static",
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
    "PUBLISHABLE_KEY": os.environ.get("STRIPE_PUBLISHABLE_KEY"),
    "SECRET_KEY": os.environ.get("STRIPE_SECRET_KEY"),
    "ENDPOINT_SECRET": os.environ.get("STRIPE_ENDPOINT_SECRET"),
}

MONGO_DB = {
    "ORG_ID": os.environ.get("MONGODB_ORG_ID"),
    "PROJECT_ID": os.environ.get("MONGODB_PROJECT_ID"),
    "CLIENT_ID": os.environ.get("MONGODB_CLIENT_ID"),
    "CLIENT_SECRET": os.environ.get("MONGODB_CLIENT_SECRET"),
}

GCP = {
    "KEY_PATH": os.environ.get("GCP_KEY_PATH"),
}

GITHUB = {
    "CLIENT_ID": os.environ.get("GITHUB_CLIENT_ID"),
    "CLIENT_SECRET": os.environ.get("GITHUB_CLIENT_SECRET"),
}

# Templates Configuration
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
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

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True