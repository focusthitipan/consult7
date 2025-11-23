"""OAuth 2.0 Device Flow implementation (RFC 8628).

Implements Device Authorization Grant for providers like GitHub Copilot
that support device-based authentication without requiring a client secret.

Flow:
1. Request device code from provider
2. Display user_code and verification_uri to user
3. Poll token endpoint until user authorizes
4. Store access token securely

Reference: https://tools.ietf.org/html/rfc8628
"""

import asyncio
import base64
import hashlib
import secrets
from typing import Optional
from urllib.parse import urlencode

import aiohttp


class DeviceFlowAuth:
    """OAuth 2.0 Device Flow authentication handler."""

    def __init__(self, client_id: str, device_code_url: str, token_url: str, scope: str):
        """Initialize Device Flow authentication.

        Args:
            client_id: OAuth client ID (public)
            device_code_url: Endpoint to request device code
            token_url: Endpoint to poll for access token
            scope: OAuth scope string
        """
        self.client_id = client_id
        self.device_code_url = device_code_url
        self.token_url = token_url
        self.scope = scope

    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier (RFC 7636).

        Returns:
            Random base64url string (43-128 chars)
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier (RFC 7636).

        Args:
            verifier: Code verifier string

        Returns:
            SHA-256 hash as base64url
        """
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    async def request_device_code(self, use_pkce: bool = False) -> dict:
        """Request device code from provider (Step 1 of Device Flow).

        Args:
            use_pkce: Whether to use PKCE (required for some providers like Qwen)

        Returns:
            Device code response with keys:
            - device_code: Code to use when polling
            - user_code: Code user enters on verification page
            - verification_uri: URL user visits
            - expires_in: Seconds until code expires
            - interval: Seconds between polling attempts
            - code_verifier: PKCE verifier (if use_pkce=True)

        Raises:
            Exception: If request fails
        """
        params = {"client_id": self.client_id, "scope": self.scope}

        code_verifier = None
        if use_pkce:
            code_verifier = self._generate_code_verifier()
            code_challenge = self._generate_code_challenge(code_verifier)
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        headers = {
            "Accept": "application/json",
            "User-Agent": "Consult7/3.0",
        }

        async with aiohttp.ClientSession() as session:
            if use_pkce:
                # POST with body (required by Qwen)
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                async with session.post(
                    self.device_code_url, data=urlencode(params), headers=headers, timeout=30
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
            else:
                # POST with query string (GitHub style)
                url = f"{self.device_code_url}?{urlencode(params)}"
                async with session.post(url, headers=headers, timeout=30) as response:
                    response.raise_for_status()
                    data = await response.json()

        if "device_code" not in data or "user_code" not in data:
            raise Exception(f"Invalid device code response: {data}")

        result = {
            "device_code": data["device_code"],
            "user_code": data["user_code"],
            "verification_uri": data.get("verification_uri_complete")
            or data.get("verification_uri")
            or data.get("verification_url"),
            "expires_in": data.get("expires_in", 900),
            "interval": data.get("interval", 5),
        }

        if code_verifier:
            result["code_verifier"] = code_verifier

        return result

    async def poll_for_token(
        self, device_code: str, interval: int = 5, code_verifier: Optional[str] = None
    ) -> dict:
        """Poll for access token (Step 2 of Device Flow).

        Args:
            device_code: Device code from request_device_code()
            interval: Seconds between polling attempts
            code_verifier: PKCE verifier (if used in request_device_code)

        Returns:
            Token response with keys:
            - access_token: OAuth access token
            - token_type: Token type (usually "bearer")
            - scope: Granted scope
            - refresh_token: Refresh token (if supported)
            - expires_in: Token lifetime in seconds (if provided)

        Raises:
            Exception: If authorization fails or expires
        """
        params = {
            "client_id": self.client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        if code_verifier:
            params["code_verifier"] = code_verifier

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Consult7/3.0",
        }

        async with aiohttp.ClientSession() as session:
            while True:
                async with session.post(
                    self.token_url, data=urlencode(params), headers=headers, timeout=30
                ) as response:
                    data = await response.json()

                    # Success - got access token
                    if response.status == 200 and "access_token" in data:
                        return {
                            "access_token": data["access_token"],
                            "token_type": data.get("token_type", "bearer"),
                            "scope": data.get("scope", self.scope),
                            "refresh_token": data.get("refresh_token"),
                            "expires_in": data.get("expires_in"),
                        }

                    # Still pending - user hasn't authorized yet
                    if "error" in data:
                        error = data["error"]

                        if error == "authorization_pending":
                            await asyncio.sleep(interval)
                            continue

                        if error == "slow_down":
                            # Provider requests slower polling
                            interval = data.get("interval", interval + 5)
                            await asyncio.sleep(interval)
                            continue

                        if error == "expired_token":
                            raise Exception(
                                "Device code expired before authorization.\n"
                                "  Hint: Complete device flow within the time limit (usually 15 minutes)"
                            )

                        if error == "access_denied":
                            raise Exception(
                                "Authorization was denied.\n"
                                "  Hint: Accept the authorization request to continue"
                            )

                        # Unknown error
                        error_desc = data.get("error_description", error)
                        raise Exception(f"OAuth error: {error_desc}")

                    # Unexpected response
                    raise Exception(f"Unexpected token response: {data}")
