"""
Production settings — used when DJANGO_SETTINGS_MODULE=core.settings.prod
"""

from core.settings.base import *  # noqa: F401, F403

# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────
DEBUG = False

# ──────────────────────────────────────────────
# Security  (base.py already sets secure defaults;
#             explicitly confirm them here for clarity)
# ──────────────────────────────────────────────
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True

# ──────────────────────────────────────────────
# Database — use Key Vault password (already set in base.py)
# ──────────────────────────────────────────────
# Password comes from KeyVaultClient in base.py — no override needed.

# ──────────────────────────────────────────────
# Logging (optional — add production logging here)
# ──────────────────────────────────────────────
# LOGGING = { ... }
