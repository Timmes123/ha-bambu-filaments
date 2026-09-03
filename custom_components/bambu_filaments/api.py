"""Synchronous client for the Bambu Lab cloud Filament Manager API.

All methods are blocking (curl_cffi) and must be called via an executor from
Home Assistant. The API surface is unofficial; see the repository README.
"""

from __future__ import annotations

from typing import Any

from curl_cffi import requests as curl_requests

IMPERSONATE = "chrome"
TIMEOUT = 20
PAGE_SIZE = 100
# Hard upper bound on pagination requests per refresh (5000 spools) so a
# misbehaving API response can never loop forever.
MAX_PAGES = 50


class BambuCloudError(Exception):
    """Base error for the Bambu cloud client."""


class CloudflareBlocked(BambuCloudError):
    """The request was blocked by Cloudflare bot protection."""


class AuthFailed(BambuCloudError):
    """Login was rejected (bad credentials or unexpected response)."""


class AuthExpired(BambuCloudError):
    """The stored token is no longer valid (HTTP 401)."""


class EmailCodeRequired(BambuCloudError):
    """Login requires an email/SMS verification code (already requested)."""


class CodeIncorrect(BambuCloudError):
    """The supplied verification code was rejected."""


class TfaRequired(BambuCloudError):
    """Login requires a two-factor (TOTP) code."""

    def __init__(self, tfa_key: str) -> None:
        super().__init__("Two-factor code required")
        self.tfa_key = tfa_key


class BambuCloudClient:
    """Minimal Bambu cloud client for the filament inventory endpoints."""

    def __init__(self, region: str, token: str | None = None) -> None:
        self._region = region
        self.token = token

    @property
    def _api(self) -> str:
        return "https://api.bambulab.cn" if self._region == "china" else "https://api.bambulab.com"

    @property
    def _web(self) -> str:
        return "https://bambulab.cn" if self._region == "china" else "https://bambulab.com"

    def _request(self, method: str, url: str, body: dict | None = None, auth: bool = True):
        headers = {}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = getattr(curl_requests, method)(
                url,
                headers=headers,
                json=body,
                timeout=TIMEOUT,
                impersonate=IMPERSONATE,
            )
        except Exception as err:
            raise BambuCloudError(f"Connection to Bambu cloud failed: {err}") from err
        if response.status_code in (403, 429) and "cloudflare" in response.text.lower():
            raise CloudflareBlocked(f"Blocked by Cloudflare (HTTP {response.status_code})")
        # Only a 401 on an authenticated request means the stored token expired;
        # login/code/TFA endpoints answer 401 for bad credentials, which the
        # callers map to their own error types.
        if response.status_code == 401 and auth and self.token:
            raise AuthExpired("Bambu cloud token rejected (HTTP 401)")
        return response

    @staticmethod
    def _json(response) -> dict[str, Any]:
        """Decode a response body, keeping failures inside the error taxonomy."""
        try:
            return response.json()
        except Exception as err:
            raise BambuCloudError(
                f"Invalid (non-JSON) response from Bambu cloud (HTTP {response.status_code})"
            ) from err

    # ------------------------------------------------------------------ auth

    def login(self, email: str, password: str) -> str:
        """Start a password login.

        Returns the token on direct success. Raises EmailCodeRequired (a code
        has been sent) or TfaRequired when an additional step is needed.
        """
        response = self._request(
            "post",
            f"{self._api}/v1/user-service/user/login",
            body={"account": email, "password": password, "apiError": ""},
            auth=False,
        )
        if response.status_code != 200:
            raise AuthFailed(f"Login failed (HTTP {response.status_code})")
        data = self._json(response)
        if token := data.get("accessToken"):
            self.token = token
            return token
        login_type = data.get("loginType")
        if login_type == "verifyCode":
            # Bambu already emails a code as part of this login attempt -
            # do NOT request another one here or the user gets two emails.
            raise EmailCodeRequired
        if login_type == "tfa":
            raise TfaRequired(data.get("tfaKey", ""))
        raise AuthFailed(f"Unexpected login response type: {login_type}")

    def request_code(self, email: str) -> None:
        """Request a fresh email (or SMS, China/phone accounts) login code."""
        if "@" in email:
            url = f"{self._api}/v1/user-service/user/sendemail/code"
            body = {"email": email, "type": "codeLogin"}
        else:
            url = f"{self._api}/v1/user-service/user/sendsmscode"
            body = {"phone": email, "type": "codeLogin"}
        response = self._request("post", url, body=body, auth=False)
        if response.status_code != 200:
            raise BambuCloudError(f"Could not request login code (HTTP {response.status_code})")

    def login_with_code(self, email: str, code: str) -> str:
        """Complete a verification-code login."""
        response = self._request(
            "post",
            f"{self._api}/v1/user-service/user/login",
            body={"account": email, "code": code},
            auth=False,
        )
        if response.status_code == 200 and (token := self._json(response).get("accessToken")):
            self.token = token
            return token
        raise CodeIncorrect(f"Verification code rejected (HTTP {response.status_code})")

    def login_with_tfa(self, tfa_key: str, code: str) -> str:
        """Complete a two-factor login. The token is returned via cookie."""
        response = self._request(
            "post",
            f"{self._web}/api/sign-in/tfa",
            body={"tfaKey": tfa_key, "tfaCode": code},
            auth=False,
        )
        token = response.cookies.get("token")
        if response.status_code == 200 and token:
            self.token = token
            return token
        raise CodeIncorrect(f"Two-factor code rejected (HTTP {response.status_code})")

    # ------------------------------------------------------- filament library

    def get_spools(self) -> list[dict[str, Any]]:
        """Fetch the full spool inventory (paginated)."""
        spools: list[dict[str, Any]] = []
        offset = 0
        for _ in range(MAX_PAGES):
            response = self._request(
                "get",
                f"{self._api}/v1/design-user-service/my/filament/v2"
                f"?offset={offset}&limit={PAGE_SIZE}",
            )
            if response.status_code != 200:
                raise BambuCloudError(
                    f"Fetching filament inventory failed (HTTP {response.status_code})"
                )
            data = self._json(response)
            hits = [h for h in (data.get("hits") or []) if isinstance(h, dict)]
            spools.extend(hits)
            total = data.get("total")
            offset += len(hits)
            if not hits or not isinstance(total, int) or offset >= total:
                break
        return spools

    def get_catalog(self) -> dict[str, Any]:
        """Fetch the canonical filament catalog (requires auth)."""
        response = self._request("get", f"{self._api}/v1/design-user-service/filament/config")
        if response.status_code != 200:
            raise BambuCloudError(f"Fetching filament catalog failed (HTTP {response.status_code})")
        return self._json(response)

    def update_spool(self, spool: dict[str, Any]) -> dict[str, Any]:
        """Update one spool. `spool` must contain at least id and filamentName."""
        response = self._request(
            "put", f"{self._api}/v1/design-user-service/my/filament/v2", body=spool
        )
        if response.status_code != 200:
            raise BambuCloudError(f"Updating spool failed (HTTP {response.status_code})")
        return self._json(response)

    def create_spool(self, spool: dict[str, Any]) -> None:
        """Create a spool. The API returns an empty body; re-fetch to see it."""
        response = self._request(
            "post", f"{self._api}/v1/design-user-service/my/filament/v2", body=spool
        )
        if response.status_code != 200:
            raise BambuCloudError(f"Creating spool failed (HTTP {response.status_code})")

    def ams_sync(self, dev_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Push AMS tray reads for one printer (what Studio does after an AMS scan).

        Unknown RFIDs are created by the server (listed in `createdRFIDs`),
        known ones get their weight/position updated; other slots are untouched.
        """
        response = self._request(
            "post",
            f"{self._api}/v1/design-user-service/my/filament/v2/ams/sync",
            body={"devId": dev_id, "items": items},
        )
        if response.status_code != 200:
            raise BambuCloudError(f"AMS sync failed (HTTP {response.status_code})")
        return self._json(response)

    def get_tasks(self, limit: int = 30) -> list[dict[str, Any]]:
        """Recent print jobs of the account (all printers), newest first."""
        response = self._request(
            "get", f"{self._api}/v1/user-service/my/tasks?limit={int(limit)}"
        )
        if response.status_code != 200:
            raise BambuCloudError(f"Fetching print jobs failed (HTTP {response.status_code})")
        data = self._json(response)
        return [h for h in (data.get("hits") or []) if isinstance(h, dict)]

    def delete_spools(self, spool_ids: list[int]) -> None:
        """Delete spools by cloud id (idempotent on the server side)."""
        response = self._request(
            "delete",
            f"{self._api}/v1/design-user-service/my/filament/v2/batch",
            body={"ids": spool_ids},
        )
        if response.status_code != 200:
            raise BambuCloudError(f"Deleting spools failed (HTTP {response.status_code})")
