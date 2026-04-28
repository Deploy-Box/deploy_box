"""
Test settings — lightweight SQLite configuration for running tests locally and in CI.
Usage: python manage.py test --settings=core.settings.test
"""

from core.settings.base import *  # noqa: F401, F403

DEBUG = False

# Use SQLite for fast, permission-free test runs
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Skip migrations and create tables directly from model definitions.
# This avoids pre-existing migration compatibility issues with SQLite.
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Relax security for tests
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

ALLOWED_HOSTS = ["*"]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
