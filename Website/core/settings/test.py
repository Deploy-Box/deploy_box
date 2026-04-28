"""
Test settings — lightweight SQLite configuration for running tests locally and in CI.
Usage: python manage.py test --settings=core.settings.test
"""

import os

os.environ.setdefault("DEPLOY_BOX_DJANGO_SECRET_KEY", "ci-test-secret-key-not-for-production")

from core.settings.base import *  # noqa: F401, F403, E402

DEBUG = False
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    os.environ.get("DEPLOY_BOX_DJANGO_SECRET_KEY", "ci-test-secret-key-not-for-production"),
)

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

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
