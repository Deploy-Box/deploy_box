"""
Production settings — used when DJANGO_SETTINGS_MODULE=core.settings.prod
"""

from core.settings.base import *  # noqa: F401, F403

# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────
DEBUG = False

# ──────────────────────────────────────────────
# Hosts
# ──────────────────────────────────────────────
_host_bare = HOST.replace("https://", "").replace("http://", "")
if _host_bare not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_host_bare)

# Refresh trusted origins with the expanded host list
CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.extend([f"https://{host}", f"http://{host}"])

# ──────────────────────────────────────────────
# Security  (base.py already sets secure defaults;
#             explicitly confirm them here for clarity)
# ──────────────────────────────────────────────
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ──────────────────────────────────────────────
# Database — use Key Vault password (already set in base.py)
# ──────────────────────────────────────────────
# Password comes from KeyVaultClient in base.py — no override needed.

# ──────────────────────────────────────────────
# Logging (optional — add production logging here)
# ──────────────────────────────────────────────
# LOGGING = { ... }
