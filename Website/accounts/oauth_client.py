# oauth_client.py
import os
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient, LegacyApplicationClient
from oauthlib.oauth2 import WebApplicationClient

import logging
logger = logging.getLogger(__name__)

class OAuth2Client:
    def __init__(self, config: dict):
        self.client_id = config["client_id"]
        print("Client id", self.client_id)
        self.client_secret = config["client_secret"]
        self.token_url = config["token_url"]
        self.authorization_base_url = config["authorization_url"]
        self.redirect_uri = config["redirect_uri"]
        self.scope = config.get("scope", [])
        self.session = None

    def get_authorization_url(self, state=None, code_challenge=None):
        """
        Step 1: Get the URL to redirect the user for OAuth2 authorization.
        Supports PKCE.
        """
        client = WebApplicationClient(client_id=self.client_id)
        self.session = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            client=client
        )
        auth_url, state = self.session.authorization_url(
            self.authorization_base_url,
            code_challenge=code_challenge,
            code_challenge_method="S256",
            state=state
        )
        return auth_url, state

    def fetch_token(self, authorization_response, code_verifier):
        """
        Step 2: Exchange authorization code for access token.
        """
        token = self.session.fetch_token(
            token_url=self.token_url,
            authorization_response=authorization_response,
            client_secret=self.client_secret,
            code_verifier=code_verifier
        )
        return token

    def refresh_token(self, refresh_token):
        """
        Use the refresh token to get a new access token.
        """
        extra = {"client_id": self.client_id, "client_secret": self.client_secret}
        new_token = self.session.refresh_token(
            self.token_url,
            refresh_token=refresh_token,
            **extra
        )
        return new_token

    def get_session(self, token):
        """
        Return an authenticated OAuth2Session.
        """
        self.session = OAuth2Session(self.client_id, token=token)
        return self.session
