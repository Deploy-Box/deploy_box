"""
Development settings — used when DJANGO_SETTINGS_MODULE=core.settings.dev
"""

from core.settings.base import *  # noqa: F401, F403

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
# Database — override password for local dev (only if explicitly set)
# ──────────────────────────────────────────────
if os.environ.get("DB_PASSWORD"):
    DATABASES["default"]["PASSWORD"] = os.environ["DB_PASSWORD"]
