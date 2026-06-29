"""
Custom PostgreSQL backend that authenticates via Microsoft Entra ID.

Overrides get_connection_params() to fetch a fresh Entra access token
each time Django opens a new database connection.  This ensures tokens
are always valid — PostgreSQL authenticates at connection time, so
persistent connections (CONN_MAX_AGE > 0) remain authenticated for
their full lifetime even after the original token expires.
"""

from django.db.backends.postgresql import base as pg_base


class DatabaseWrapper(pg_base.DatabaseWrapper):

    def get_connection_params(self):
        params = super().get_connection_params()
        # Lazy import avoids circular imports and module-level Azure SDK init
        from core.utils.db_auth import get_azure_postgres_token

        params["password"] = get_azure_postgres_token()
        return params
