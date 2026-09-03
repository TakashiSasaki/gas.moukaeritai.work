"""Shared OAuth bearer-token acquisition for direct Google API clients.

Direct Drive and Apps Script API stages use this provider. It reads clasp's
stored authorized-user credentials for compatibility, but it does not mutate
clasp's credential store. clasp commands remain responsible for their own OAuth
refresh and persistence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(RuntimeError):
    """Raised when direct Google API bearer-token acquisition cannot proceed."""


def credentials_path(path: Path | None = None) -> Path:
    return path if path is not None else Path.home() / ".clasprc.json"


def load_authorized_user_credentials(
    path: Path | None = None,
    *,
    user: str = "default",
) -> dict[str, Any]:
    """Load one authorized-user credential from supported clasp store shapes.

    Modern clasp stores credentials under ``tokens.<user>``. The legacy local
    shape stores token fields under ``token`` and OAuth client settings under
    ``oauth2ClientSettings``. No clasp default client ID is hard-coded here:
    direct API access requires the credential store to identify its OAuth
    client explicitly.
    """
    source = credentials_path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GoogleOAuthError(f"Google OAuth credential file is missing: {source}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GoogleOAuthError(f"Cannot read Google OAuth credentials from {source}: {exc}") from exc

    if not isinstance(payload, dict):
        raise GoogleOAuthError(f"Google OAuth credential file must contain an object: {source}")

    tokens = payload.get("tokens")
    if isinstance(tokens, dict) and isinstance(tokens.get(user), dict):
        return dict(tokens[user])

    if user == "default" and isinstance(payload.get("token"), dict):
        credential = dict(payload["token"])
        settings = payload.get("oauth2ClientSettings")
        if isinstance(settings, dict):
            if not credential.get("client_id") and settings.get("clientId"):
                credential["client_id"] = settings["clientId"]
            if "client_secret" not in credential and settings.get("clientSecret") is not None:
                credential["client_secret"] = settings["clientSecret"]
        return credential

    # Accept an explicit authorized-user object at the root only when it carries
    # the fields required for direct refresh. This does not guess clasp's
    # built-in OAuth client for legacy token-only stores.
    if user == "default" and payload.get("refresh_token") and payload.get("client_id"):
        return dict(payload)

    raise GoogleOAuthError(f"No Google OAuth credentials found for user {user!r} in {source}")


def acquire_access_token(
    path: Path | None = None,
    *,
    user: str = "default",
    session: Any = requests,
) -> str:
    """Refresh and return an ephemeral bearer token for direct Google API I/O."""
    credential = load_authorized_user_credentials(path, user=user)
    refresh_token = credential.get("refresh_token")
    client_id = credential.get("client_id")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise GoogleOAuthError("Google OAuth credential is missing a non-empty refresh_token")
    if not isinstance(client_id, str) or not client_id:
        raise GoogleOAuthError(
            "Google OAuth credential is missing client_id; direct API access will not guess clasp's default OAuth client"
        )

    request_data: dict[str, str] = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    client_secret = credential.get("client_secret")
    if isinstance(client_secret, str) and client_secret:
        request_data["client_secret"] = client_secret

    try:
        response = session.post(TOKEN_URL, data=request_data)
    except Exception as exc:
        raise GoogleOAuthError(f"Google OAuth token refresh request failed: {exc}") from exc

    if getattr(response, "status_code", None) != 200:
        status = getattr(response, "status_code", "unknown")
        raise GoogleOAuthError(f"Google OAuth token refresh failed with HTTP status {status}")
    try:
        payload = response.json()
    except Exception as exc:
        raise GoogleOAuthError(f"Google OAuth token refresh returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise GoogleOAuthError("Google OAuth token refresh response must be a JSON object")
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleOAuthError("Google OAuth token refresh response has no non-empty access_token")
    return access_token
