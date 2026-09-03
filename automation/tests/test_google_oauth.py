from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.shared import google_oauth


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response=None):
        self.response = response or FakeResponse({"access_token": "fresh"})
        self.calls = []

    def post(self, url, data):
        self.calls.append((url, dict(data)))
        return self.response


class GoogleOAuthTests(unittest.TestCase):
    def test_modern_clasp_store_refreshes_without_requiring_client_secret(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".clasprc.json"
            path.write_text(json.dumps({
                "tokens": {
                    "default": {
                        "client_id": "client",
                        "refresh_token": "refresh",
                    }
                }
            }), encoding="utf-8")
            session = FakeSession()
            self.assertEqual("fresh", google_oauth.acquire_access_token(path, session=session))
            self.assertEqual(google_oauth.TOKEN_URL, session.calls[0][0])
            self.assertEqual({
                "client_id": "client",
                "refresh_token": "refresh",
                "grant_type": "refresh_token",
            }, session.calls[0][1])

    def test_legacy_local_store_combines_token_and_client_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".clasprc.json"
            path.write_text(json.dumps({
                "token": {"refresh_token": "refresh"},
                "oauth2ClientSettings": {
                    "clientId": "legacy-client",
                    "clientSecret": "legacy-secret",
                },
            }), encoding="utf-8")
            credentials = google_oauth.load_authorized_user_credentials(path)
            self.assertEqual("legacy-client", credentials["client_id"])
            self.assertEqual("legacy-secret", credentials["client_secret"])
            session = FakeSession()
            self.assertEqual("fresh", google_oauth.acquire_access_token(path, session=session))
            self.assertEqual("legacy-secret", session.calls[0][1]["client_secret"])

    def test_direct_refresh_refuses_to_guess_missing_client_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".clasprc.json"
            path.write_text(json.dumps({
                "tokens": {"default": {"refresh_token": "refresh"}}
            }), encoding="utf-8")
            with self.assertRaisesRegex(google_oauth.GoogleOAuthError, "client_id"):
                google_oauth.acquire_access_token(path, session=FakeSession())

    def test_refresh_http_failure_preserves_safe_google_error_details_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".clasprc.json"
            path.write_text(json.dumps({
                "tokens": {"default": {"client_id": "client", "refresh_token": "refresh"}}
            }), encoding="utf-8")
            response = FakeResponse({
                "error": "invalid_grant",
                "error_description": "Token has been revoked",
                "refresh_token": "must-not-be-reported",
            }, status_code=400)
            with self.assertRaises(google_oauth.GoogleOAuthError) as raised:
                google_oauth.acquire_access_token(path, session=FakeSession(response))
            message = str(raised.exception)
            self.assertIn("HTTP status 400", message)
            self.assertIn("error=invalid_grant", message)
            self.assertIn("error_description=Token has been revoked", message)
            self.assertNotIn("must-not-be-reported", message)

    def test_refresh_requires_access_token_in_response(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".clasprc.json"
            path.write_text(json.dumps({
                "tokens": {"default": {"client_id": "client", "refresh_token": "refresh"}}
            }), encoding="utf-8")
            with self.assertRaisesRegex(google_oauth.GoogleOAuthError, "access_token"):
                google_oauth.acquire_access_token(
                    path,
                    session=FakeSession(FakeResponse({})),
                )


if __name__ == "__main__":
    unittest.main()
