"""
Development settings — used when DJANGO_SETTINGS_MODULE=core.settings.dev
"""

import ssl

from core.settings.base import *  # noqa: F401, F403

# ──────────────────────────────────────────────
# Disable SSL verification for local dev (corporate proxy workaround)
# ──────────────────────────────────────────────
ssl._create_default_https_context = ssl._create_unverified_context  # noqa: SLF001

# Use OS certificate store for requests/urllib3 (fixes Stripe API behind Cato Networks proxy)
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import httpx  # noqa: E402
_original_client_init = httpx.Client.__init__

def _patched_client_init(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    _original_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_client_init

# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────
DEBUG = True

ALLOWED_HOSTS += [
    "127.0.0.1",
    "localhost",
    HOST.replace("https://", "").replace("http://", ""),
]

# Refresh trusted origins with the expanded host list
CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.extend([f"https://{host}", f"http://{host}"])

# ──────────────────────────────────────────────
# Dev-only apps & middleware
# ──────────────────────────────────────────────
INSTALLED_APPS += [
    "django_browser_reload",
    "django_extensions",
]

# ──────────────────────────────────────────────
# Relax security for local development
# ──────────────────────────────────────────────
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# ──────────────────────────────────────────────
# Database — fall back to static password for Docker or Azure PostgreSQL
# (requires DB_HOST, DB_NAME, DB_USER, DB_PORT set appropriately)
# ──────────────────────────────────────────────
if os.environ.get("DB_PASSWORD"):
    DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"
    DATABASES["default"]["PASSWORD"] = os.environ["DB_PASSWORD"]
    # Keep SSL for Azure PostgreSQL; disable for local Docker
    if "database.azure.com" not in os.environ.get("DB_HOST", ""):
        DATABASES["default"]["OPTIONS"] = {}  # no SSL for local Docker
