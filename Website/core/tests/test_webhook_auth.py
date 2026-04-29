import hashlib
import hmac
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed

from core.utils.webhook_auth import verify_iac_webhook_signature


class VerifyIACWebhookSignatureTest(TestCase):
    """Tests for the HMAC-SHA256 IaC webhook signature verifier."""

    WEBHOOK_SECRET = "test-secret-key"

    def _make_request(self, data, signature=None):
        """Build a mock request with META headers and .data attribute."""
        request = MagicMock()
        request.data = data
        request.META = {}
        if signature is not None:
            request.META["HTTP_X_WEBHOOK_SIGNATURE_256"] = signature
        return request

    def _compute_signature(self, data):
        body = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
        return "sha256=" + hmac.new(
            self.WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()

    @patch("core.utils.webhook_auth._kv")
    def test_valid_signature_passes(self, mock_kv):
        mock_kv.get_secret.return_value = self.WEBHOOK_SECRET
        data = {"stack_id": "abc123", "status": "completed"}
        sig = self._compute_signature(data)
        request = self._make_request(data, signature=sig)
        # Should not raise
        verify_iac_webhook_signature(request)

    @patch("core.utils.webhook_auth._kv")
    def test_missing_signature_header_raises(self, mock_kv):
        request = self._make_request({"key": "value"}, signature=None)
        with self.assertRaises(AuthenticationFailed) as ctx:
            verify_iac_webhook_signature(request)
        self.assertIn("Missing webhook signature", str(ctx.exception))

    @patch("core.utils.webhook_auth._kv")
    def test_missing_secret_raises(self, mock_kv):
        mock_kv.get_secret.return_value = None
        request = self._make_request({"key": "value"}, signature="sha256=abc")
        with self.assertRaises(AuthenticationFailed) as ctx:
            verify_iac_webhook_signature(request)
        self.assertIn("not configured", str(ctx.exception))

    @patch("core.utils.webhook_auth._kv")
    def test_invalid_signature_raises(self, mock_kv):
        mock_kv.get_secret.return_value = self.WEBHOOK_SECRET
        data = {"stack_id": "abc123"}
        request = self._make_request(data, signature="sha256=invalid_hex_digest")
        with self.assertRaises(AuthenticationFailed) as ctx:
            verify_iac_webhook_signature(request)
        self.assertIn("Invalid webhook signature", str(ctx.exception))

    @patch("core.utils.webhook_auth._kv")
    def test_tampered_payload_rejected(self, mock_kv):
        mock_kv.get_secret.return_value = self.WEBHOOK_SECRET
        original = {"stack_id": "abc123", "status": "completed"}
        sig = self._compute_signature(original)
        tampered = {"stack_id": "abc123", "status": "HACKED"}
        request = self._make_request(tampered, signature=sig)
        with self.assertRaises(AuthenticationFailed):
            verify_iac_webhook_signature(request)
