"""Gemini CLI provider implementation for Consult7."""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple
import httpx
import time

from .base import BaseProvider, process_llm_response
from ..constants import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_OUTPUT_TOKENS,
    DEFAULT_TEMPERATURE,
    OPENROUTER_TIMEOUT,
)

logger = logging.getLogger("consult7")

# OAuth2 Configuration
OAUTH_REDIRECT_URI = "http://localhost:45289"

# Default OAuth Client Credentials (from Gemini CLI / kilocode)
# These are the same credentials used by kilocode and official Gemini CLI
# Source: https://api.kilocode.ai/extension-config.json (public config)
DEFAULT_OAUTH_CLIENT_ID = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
DEFAULT_OAUTH_CLIENT_SECRET = "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"

# Code Assist API Configuration
CODE_ASSIST_ENDPOINT = "https://cloudcode-pa.googleapis.com"
CODE_ASSIST_API_VERSION = "v1internal"

# Default models and context
# Note: OAuth รองรับเฉพาะ Gemini 2.5 Series เท่านั้น
# gemini-1.5-pro, gemini-1.5-flash, gemini-1.0-pro = HTTP 404
GEMINI_CLI_MODELS = {
    "gemini-2.5-flash": {
        "context_length": 1_048_576,
        "max_tokens": 64_000,
        "description": "Fast (2s response, 49 tokens)",
    },
    "gemini-2.5-flash-lite": {
        "context_length": 1_048_576,
        "max_tokens": 64_000,
        "description": "Ultra fast, lightweight, for simple tasks",
    },
    "gemini-2.5-pro": {
        "context_length": 1_048_576,
        "max_tokens": 64_000,
        "description": "High quality (25s response)",
    },
}
DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiCliProvider(BaseProvider):
    """Gemini CLI provider implementation using OAuth2."""

    def __init__(self):
        """Initialize Gemini CLI provider."""
        self.credentials: Optional[dict] = None
        self.project_id: Optional[str] = None
        self._oauth_path: Optional[str] = None

    def _get_credentials_path(self, custom_path: Optional[str] = None) -> Path:
        """Get the path to OAuth credentials file."""
        if custom_path:
            return Path(custom_path).expanduser()
        return Path.home() / ".gemini" / "oauth_creds.json"

    def _is_token_valid(self) -> bool:
        """Check if current token is valid (proactive check)."""
        if not self.credentials:
            return False

        # Check if access_token exists
        if not self.credentials.get("access_token"):
            return False

        # Check expiry_date (with 30 second buffer)
        expiry_date = self.credentials.get("expiry_date")
        if not expiry_date:
            return False

        # Token is valid if not expired (30s buffer)
        current_time_ms = time.time() * 1000
        return current_time_ms < (expiry_date - 30000)

    async def _load_oauth_credentials(self, oauth_path: Optional[str] = None) -> None:
        """Load OAuth credentials from file."""
        try:
            cred_path = self._get_credentials_path(oauth_path)
            self._oauth_path = str(cred_path)

            if not cred_path.exists():
                raise FileNotFoundError(
                    f"OAuth credentials not found at {cred_path}. "
                    f"Please run 'gemini' CLI tool first to authenticate."
                )

            with open(cred_path, "r") as f:
                cred_data = json.load(f)

            # Store credentials as dict (like kilocode does)
            self.credentials = cred_data

            logger.debug(f"OAuth credentials loaded, expires at: {cred_data.get('expiry_date')}")

        except Exception as e:
            raise RuntimeError(f"Failed to load Gemini CLI OAuth credentials: {e}")

    async def _refresh_access_token(self) -> None:
        """Refresh OAuth access token manually (similar to kilocode implementation)."""
        if not self.credentials or not self.credentials.get("refresh_token"):
            raise RuntimeError("No refresh token available")

        try:
            # Prepare refresh request (using kilocode's public OAuth credentials)
            refresh_data = {
                "client_id": DEFAULT_OAUTH_CLIENT_ID,
                "client_secret": DEFAULT_OAUTH_CLIENT_SECRET,
                "refresh_token": self.credentials["refresh_token"],
                "grant_type": "refresh_token",
            }

            logger.info("Refreshing Gemini CLI OAuth token...")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=refresh_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_text = response.text[:500]
                    logger.error(f"Token refresh failed: {response.status_code} - {error_text}")
                    raise RuntimeError(f"Token refresh failed: {response.status_code}")

                token_data = response.json()

                if "error" in token_data:
                    raise RuntimeError(f"Token refresh error: {token_data.get('error_description', token_data['error'])}")

                # Update credentials (preserve refresh_token if not returned)
                self.credentials["access_token"] = token_data["access_token"]
                self.credentials["token_type"] = token_data.get("token_type", "Bearer")
                self.credentials["expiry_date"] = int(time.time() * 1000) + (token_data.get("expires_in", 3600) * 1000)

                # Update refresh_token if provided
                if "refresh_token" in token_data:
                    self.credentials["refresh_token"] = token_data["refresh_token"]

                logger.info("Gemini CLI token refreshed successfully")

                # Save to file
                if self._oauth_path:
                    with open(self._oauth_path, "w") as f:
                        json.dump(self.credentials, f, indent=2)
                    logger.debug(f"Refreshed credentials saved to {self._oauth_path}")

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise RuntimeError(
                f"Failed to refresh OAuth token: {e}\n"
                f"Please re-authenticate using 'gemini' CLI tool."
            )

    async def _ensure_authenticated(self, oauth_path: Optional[str] = None) -> None:
        """Ensure OAuth credentials are loaded and valid (proactive check)."""
        # Load credentials if not already loaded
        if not self.credentials:
            await self._load_oauth_credentials(oauth_path)
            logger.info("Gemini CLI OAuth credentials loaded")

        # Proactive token validity check and refresh if needed
        if not self._is_token_valid():
            logger.info("Gemini CLI token invalid or expired, refreshing...")
            await self._refresh_access_token()

    async def _discover_project_id(self) -> str:
        """Discover or retrieve the project ID."""
        if self.project_id:
            return self.project_id

        # Check environment variable
        env_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if env_project_id:
            self.project_id = env_project_id
            return self.project_id

        # Default project ID for personal OAuth
        initial_project_id = "default"

        # Prepare client metadata
        client_metadata = {
            "ideType": "IDE_UNSPECIFIED",
            "platform": "PLATFORM_UNSPECIFIED",
            "pluginType": "GEMINI",
            "duetProject": initial_project_id,
        }

        try:
            # Call loadCodeAssist
            load_request = {
                "cloudaicompanionProject": initial_project_id,
                "metadata": client_metadata,
            }

            load_response = await self._call_endpoint("loadCodeAssist", load_request)

            if load_response.get("cloudaicompanionProject"):
                self.project_id = load_response["cloudaicompanionProject"]
                return self.project_id

            # If no existing project, onboard
            default_tier = next(
                (tier for tier in load_response.get("allowedTiers", []) if tier.get("isDefault")),
                None,
            )
            tier_id = default_tier["id"] if default_tier else "free-tier"

            # FREE tier: don't send project, Google will assign managed project
            onboard_request = {
                "tierId": tier_id,
                "metadata": client_metadata,
            }

            lro_response = await self._call_endpoint("onboardUser", onboard_request)

            # Poll until done (max 30 retries = 60 seconds)
            retry_count = 0
            while not lro_response.get("done") and retry_count < 30:
                await asyncio.sleep(2)
                lro_response = await self._call_endpoint("onboardUser", onboard_request)
                retry_count += 1

            if not lro_response.get("done"):
                raise RuntimeError("Onboarding timeout - operation did not complete")

            discovered_id = (
                lro_response.get("response", {}).get("cloudaicompanionProject", {}).get("id")
                or initial_project_id
            )
            self.project_id = discovered_id
            return self.project_id

        except Exception as e:
            logger.error(f"Failed to discover project ID: {e}")
            raise RuntimeError("Failed to discover Gemini CLI project ID")

    async def _call_endpoint(self, method: str, body: dict, retry_auth: bool = True) -> dict:
        """Call a Code Assist API endpoint."""
        # Proactively ensure authentication before every API call
        await self._ensure_authenticated(self._oauth_path)

        if not self.credentials or not self.credentials.get("access_token"):
            raise RuntimeError("OAuth credentials not authenticated after refresh attempt")

        url = f"{CODE_ASSIST_ENDPOINT}/{CODE_ASSIST_API_VERSION}:{method}"
        headers = {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=body, timeout=OPENROUTER_TIMEOUT
                )

                # Handle 401 with retry (token might have expired during request)
                if response.status_code == 401 and retry_auth:
                    logger.warning(f"Got 401 on {method}, refreshing token and retrying...")
                    # Force token refresh
                    self.credentials = None
                    await self._ensure_authenticated(self._oauth_path)
                    return await self._call_endpoint(method, body, retry_auth=False)

                if response.status_code != 200:
                    error_detail = response.text[:500]  # Limit error message length
                    logger.error(f"API error on {method}: {response.status_code} - {error_detail}")
                    raise RuntimeError(
                        f"API error: {response.status_code} - {error_detail}"
                    )

                return response.json()

        except httpx.TimeoutException:
            logger.error(f"Request timeout on {method} after {OPENROUTER_TIMEOUT} seconds")
            raise RuntimeError(f"Request timeout after {OPENROUTER_TIMEOUT} seconds")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error on {method}: {e}")
            raise RuntimeError(f"Invalid JSON response from API: {e}")
        except Exception as e:
            logger.error(f"API call failed on {method}: {e}")
            raise RuntimeError(f"API call failed: {e}")

    async def get_model_info(self, model_name: str, api_key: Optional[str]) -> Optional[dict]:
        """Get model information.

        Note: api_key is ignored for Gemini CLI (uses OAuth).
        """
        # Extract base model name (remove :thinking suffix if present)
        base_model = model_name.replace(":thinking", "")

        if base_model in GEMINI_CLI_MODELS:
            model_info = GEMINI_CLI_MODELS[base_model]
            return {
                "context_length": model_info["context_length"],
                "max_output_tokens": model_info["max_tokens"],
                "provider": "gemini-cli",
            }

        # Default fallback
        return {
            "context_length": DEFAULT_CONTEXT_LENGTH,
            "max_output_tokens": DEFAULT_OUTPUT_TOKENS,
            "provider": "gemini-cli",
        }

    async def call_llm(
        self,
        content: str,
        query: str,
        model_name: str,
        api_key: str,
        thinking_mode: bool = False,
        thinking_budget: Optional[int] = None,
    ) -> Tuple[str, Optional[str], Optional[int]]:
        """Call Gemini CLI API with the content and query.

        Args:
            api_key: OAuth path (format: "oauth:/path/to/oauth_creds.json")
                    If starts with "oauth:", extracts path after colon

        Returns:
            Tuple of (response, error, reasoning_tokens_used)
        """
        try:
            # Parse OAuth path from api_key
            oauth_path = None
            if api_key and api_key.startswith("oauth:"):
                oauth_path = api_key[6:]  # Remove "oauth:" prefix
                if not oauth_path:  # Empty path after "oauth:"
                    oauth_path = None

            # Proactively ensure authenticated before any API calls
            await self._ensure_authenticated(oauth_path)
            logger.info("Gemini CLI authentication verified, discovering project ID...")

            # Discover project ID (this will also ensure authentication)
            project_id = await self._discover_project_id()
            logger.info(f"Gemini CLI project ID: {project_id}")

            # Extract base model name
            base_model = model_name.replace(":thinking", "")
            if base_model not in GEMINI_CLI_MODELS:
                base_model = DEFAULT_MODEL

            # Prepare messages (combine system + user into single user message)
            # Note: Gemini Code Assist API doesn't support 'system' role or systemInstruction
            # Must combine everything into user messages
            system_instruction = (
                "You are a helpful assistant analyzing code and files. "
                "Be concise and specific in your responses."
            )
            user_message = f"{system_instruction}\n\nHere are the files to analyze:\n\n{content}\n\nQuery: {query}"

            # Build request (similar to ai-gateway implementation)
            request_body = {
                "model": base_model,
                "project": project_id,
                "request": {
                    "contents": [
                        {"role": "user", "parts": [{"text": user_message}]},
                    ],
                    "generationConfig": {
                        "temperature": DEFAULT_TEMPERATURE,
                        "maxOutputTokens": GEMINI_CLI_MODELS[base_model]["max_tokens"],
                    },
                },
            }

            # Add thinking config if requested
            if thinking_mode and thinking_budget:
                request_body["request"]["generationConfig"]["thinkingConfig"] = {
                    "thinkingBudget": thinking_budget
                }

            # Call streaming endpoint
            url = f"{CODE_ASSIST_ENDPOINT}/{CODE_ASSIST_API_VERSION}:streamGenerateContent"
            headers = {
                "Authorization": f"Bearer {self.credentials['access_token']}",
                "Content-Type": "application/json",
            }

            full_response = ""
            reasoning_text = ""
            total_reasoning_tokens = 0

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=request_body,
                    params={"alt": "sse"},
                    timeout=OPENROUTER_TIMEOUT,
                ) as response:
                    if response.status_code != 200:
                        return "", f"API error: {response.status_code}", None

                    # Parse SSE stream
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:].strip()
                            if data == "[DONE]":
                                continue

                            try:
                                chunk = json.loads(data)
                                response_data = chunk.get("response", chunk)
                                candidate = response_data.get("candidates", [{}])[0]

                                # Extract content
                                if candidate.get("content", {}).get("parts"):
                                    for part in candidate["content"]["parts"]:
                                        if part.get("text"):
                                            if part.get("thought"):
                                                reasoning_text += part["text"]
                                            else:
                                                full_response += part["text"]

                                # Track usage
                                usage = response_data.get("usageMetadata")
                                if usage:
                                    total_reasoning_tokens = usage.get("thoughtsTokenCount", 0)

                                # Check if done
                                if candidate.get("finishReason"):
                                    break

                            except json.JSONDecodeError:
                                continue

            # Process response
            processed_response = process_llm_response(full_response)

            return (
                processed_response,
                None,
                total_reasoning_tokens if thinking_mode else None,
            )

        except httpx.TimeoutException:
            return "", f"Request timeout after {OPENROUTER_TIMEOUT} seconds", None
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini CLI API error: {error_msg}")
            logger.error(f"Error type: {type(e).__name__}")

            # Provide more helpful error messages
            if "403" in error_msg:
                return "", (
                    f"API error: 403 Forbidden\n\n"
                    f"This usually means:\n"
                    f"1. OAuth token is invalid or expired - try running 'gemini' CLI to re-authenticate\n"
                    f"2. User needs onboarding - the project ID discovery may have failed\n"
                    f"3. API permissions issue with your Google account\n\n"
                    f"Original error: {error_msg}"
                ), None

            return "", error_msg, None


# Import asyncio at module level for sleep
import asyncio
