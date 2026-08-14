import json

from django.test import TestCase, RequestFactory

from core.helpers.request_helpers import assertRequestFields, MissingFieldError


class AssertRequestFieldsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _json_request(self, data):
        return self.factory.post(
            "/test/",
            data=json.dumps(data),
            content_type="application/json",
        )

    def _form_request(self, data):
        return self.factory.post(
            "/test/",
            data=data,
            content_type="application/x-www-form-urlencoded",
        )

    # ── JSON body ───────────────────────────────────────────────────────────

    def test_required_fields_returned_in_order(self):
        request = self._json_request({"name": "Alice", "email": "a@b.com"})
        result = assertRequestFields(request, required_fields=["name", "email"])
        self.assertEqual(result, ("Alice", "a@b.com"))

    def test_optional_field_present(self):
        request = self._json_request({"name": "Alice", "role": "admin"})
        result = assertRequestFields(
            request, required_fields=["name"], optional_fields=["role"]
        )
        self.assertEqual(result, ("Alice", "admin"))

    def test_optional_field_missing_returns_empty_string(self):
        request = self._json_request({"name": "Alice"})
        result = assertRequestFields(
            request, required_fields=["name"], optional_fields=["role"]
        )
        self.assertEqual(result, ("Alice", ""))

    def test_missing_required_field_raises(self):
        request = self._json_request({"name": "Alice"})
        with self.assertRaises(MissingFieldError) as ctx:
            assertRequestFields(request, required_fields=["name", "email"])
        self.assertIn("email", ctx.exception.message)

    def test_invalid_json_raises(self):
        request = self.factory.post(
            "/test/", data="not-json", content_type="application/json"
        )
        with self.assertRaises(MissingFieldError) as ctx:
            assertRequestFields(request, required_fields=["name"])
        self.assertIn("Invalid JSON", ctx.exception.message)

    # ── Form-urlencoded body ────────────────────────────────────────────────

    def test_form_urlencoded_required_fields(self):
        request = self._form_request("name=Alice&email=a%40b.com")
        result = assertRequestFields(
            request,
            required_fields=["name", "email"],
            mimetype="application/x-www-form-urlencoded",
        )
        self.assertEqual(result, ("Alice", "a@b.com"))

    # ── Header mode ─────────────────────────────────────────────────────────

    def test_header_mode_reads_from_headers(self):
        request = self.factory.get("/test/", HTTP_X_API_KEY="secret123")
        result = assertRequestFields(
            request,
            required_fields=["X-Api-Key"],
            body_or_header="header",
        )
        self.assertEqual(result, ("secret123",))

    # ── MissingFieldError ───────────────────────────────────────────────────

    def test_missing_field_error_to_response(self):
        err = MissingFieldError("Missing field: name", status=400)
        response = err.to_response()
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Missing field: name", response.content)
