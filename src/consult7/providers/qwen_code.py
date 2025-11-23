"""Qwen Code provider implementation for Consult7."""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple
import httpx
from openai import AsyncOpenAI

from .base import BaseProvider, process_llm_response
from ..constants import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_OUTPUT_TOKENS,
)

logger = logging.getLogger("consult7")

# OAuth Configuration
QWEN_OAUTH_BASE_URL = "https://chat.qwen.ai"
QWEN_OAUTH_TOKEN_ENDPOINT = f"{QWEN_OAUTH_BASE_URL}/api/v1/oauth2/token"
QWEN_OAUTH_CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"

# Default models
# Note: OAuth รองรับเฉพาะ qwen3-coder-plus เท่านั้น
# Models อื่นต้องใช้ API Key แทน OAuth
QWEN_CODE_MODELS = {
    "qwen3-coder-plus": {
        "context_length": 1_000_000,
        "max_tokens": 65_536,
        "description": "Code-focused model with 1M context window for large codebases (OAuth supported)",
    },
    "qwen3-coder-flash": {
        "context_length": 1_000_000,
        "max_tokens": 65_536,
        "description": "Fast coding model with 1M context window optimized for speed (OAuth supported)",
    },
}
DEFAULT_MODEL = "qwen3-coder-plus"


class QwenCodeProvider(BaseProvider):
    """Qwen Code provider implementation using OAuth2."""

    def __init__(self):
        """Initialize Qwen Code provider."""
        self.credentials: Optional[dict] = None
        self.client: Optional[AsyncOpenAI] = None
        self._oauth_path: Optional[str] = None
        self._refresh_lock = False

    def _get_credentials_path(self, custom_path: Optional[str] = None) -> Path:
        """Get the path to OAuth credentials file."""
        if custom_path:
            return Path(custom_path).expanduser()
        return Path.home() / ".qwen" / "oauth_creds.json"

    async def _load_oauth_credentials(self, oauth_path: Optional[str] = None) -> None:
        """Load OAuth credentials from file."""
        try:
            cred_path = self._get_credentials_path(oauth_path)
            self._oauth_path = str(cred_path)

            if not cred_path.exists():
                raise FileNotFoundError(
                    f"OAuth credentials not found at {cred_path}. "
                    f"Please run Qwen Code authentication first."
                )

            with open(cred_path, "r") as f:
                self.credentials = json.load(f)

        except Exception as e:
            raise RuntimeError(f"Failed to load Qwen Code OAuth credentials: {e}")

    def _is_token_valid(self) -> bool:
        """Check if current token is valid (proactive check)."""
        if not self.credentials:
            logger.debug("No credentials loaded")
            return False

        # Check access token exists
        if not self.credentials.get("access_token"):
            logger.debug("No access token in credentials")
            return False

        # Check expiry date
        expiry_date = self.credentials.get("expiry_date")
        if not expiry_date:
            logger.debug("No expiry date in credentials")
            return False

        # 30 second buffer for proactive refresh
        TOKEN_REFRESH_BUFFER_MS = 30 * 1000
        import time

        is_valid = time.time() * 1000 < expiry_date - TOKEN_REFRESH_BUFFER_MS
        if not is_valid:
            logger.debug(f"Token expired or expiring soon (expiry: {expiry_date})")

        return is_valid

    async def _refresh_access_token(self) -> None:
        """Refresh the OAuth access token."""
        if self._refresh_lock:
            # Another refresh is in progress, wait a bit
            logger.debug("Token refresh already in progress, waiting...")
            import asyncio

            await asyncio.sleep(1)
            return

        self._refresh_lock = True
        logger.info("Starting Qwen Code token refresh...")
        try:
            if not self.credentials or not self.credentials.get("refresh_token"):
                raise RuntimeError(
                    "No refresh token available. Please re-authenticate using Qwen Code OAuth flow."
                )

            body_data = {
                "grant_type": "refresh_token",
                "refresh_token": self.credentials["refresh_token"],
                "client_id": QWEN_OAUTH_CLIENT_ID,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    QWEN_OAUTH_TOKEN_ENDPOINT,
                    data=body_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Origin": "https://chat.qwen.ai",
                        "Referer": "https://chat.qwen.ai/",
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_text = response.text[:500]  # Limit error message
                    logger.error(f"Token refresh failed: {response.status_code} - {error_text}")
                    raise RuntimeError(
                        f"Token refresh failed: {response.status_code} - {error_text}"
                    )

                # Handle non-JSON response
                try:
                    token_data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Token refresh returned non-JSON response: {response.text[:200]}")
                    raise RuntimeError(
                        f"Token refresh returned invalid JSON: {e}\n"
                        f"Response: {response.text[:200]}"
                    )

                if "error" in token_data:
                    error_msg = f"{token_data['error']} - {token_data.get('error_description', '')}"
                    logger.error(f"Token refresh API error: {error_msg}")
                    raise RuntimeError(f"Token refresh failed: {error_msg}")

                # Update credentials
                import time

                self.credentials["access_token"] = token_data["access_token"]
                self.credentials["token_type"] = token_data.get("token_type", "Bearer")
                self.credentials["refresh_token"] = token_data.get(
                    "refresh_token", self.credentials["refresh_token"]
                )
                self.credentials["expiry_date"] = int(
                    (time.time() + token_data.get("expires_in", 3600)) * 1000
                )

                logger.info("Qwen Code token refreshed successfully")

                # Save to file
                if self._oauth_path:
                    with open(self._oauth_path, "w") as f:
                        json.dump(self.credentials, f, indent=2)
                    logger.debug(f"Refreshed credentials saved to {self._oauth_path}")

        except Exception as e:
            logger.error(f"Token refresh exception: {e}")
            raise
        finally:
            self._refresh_lock = False

    def _get_base_url(self) -> str:
        """Get the base URL for API calls.
        
        OAuth returns resource_url (e.g., "portal.qwen.ai") which is the API base domain.
        The correct endpoint is: https://portal.qwen.ai/v1 (NOT /compatible-mode/v1)
        """
        if not self.credentials:
            # Fallback to DashScope (for API key auth)
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"

        resource_url = self.credentials.get(
            "resource_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # Add protocol if missing
        if not resource_url.startswith("http://") and not resource_url.startswith("https://"):
            resource_url = f"https://{resource_url}"

        # OAuth endpoints use /v1 directly (NOT /compatible-mode/v1)
        # portal.qwen.ai uses: https://portal.qwen.ai/v1
        if resource_url.endswith("/v1"):
            base_url = resource_url
        else:
            base_url = f"{resource_url}/v1"

        logger.info(f"Qwen Code base URL: {base_url}")
        return base_url

    async def _ensure_authenticated(self, oauth_path: Optional[str] = None) -> None:
        """Ensure OAuth credentials are loaded and valid (proactive check)."""
        # Load credentials if not already loaded
        if not self.credentials:
            await self._load_oauth_credentials(oauth_path)
            logger.info("Qwen Code OAuth credentials loaded")

        # Proactive token validity check and refresh
        if not self._is_token_valid():
            logger.info("Qwen Code token invalid or expired, refreshing...")
            await self._refresh_access_token()

        # Create or update client with latest credentials
        if not self.client or self.client.api_key != self.credentials["access_token"]:
            self.client = AsyncOpenAI(
                api_key=self.credentials["access_token"], base_url=self._get_base_url()
            )
            logger.debug(f"OpenAI client updated with base_url: {self._get_base_url()}")

    async def get_model_info(self, model_name: str, api_key: Optional[str]) -> Optional[dict]:
        """Get model information.

        Note: api_key is ignored for Qwen Code (uses OAuth).
        """
        if model_name in QWEN_CODE_MODELS:
            model_info = QWEN_CODE_MODELS[model_name]
            return {
                "context_length": model_info["context_length"],
                "max_output_tokens": model_info["max_tokens"],
                "provider": "qwen-code",
            }

        # Default fallback
        return {
            "context_length": DEFAULT_CONTEXT_LENGTH,
            "max_output_tokens": DEFAULT_OUTPUT_TOKENS,
            "provider": "qwen-code",
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
        """Call Qwen Code API with the content and query.

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
            logger.info("Qwen Code authentication verified")

            if not self.client:
                error_msg = "OpenAI client not initialized after authentication"
                logger.error(error_msg)
                return "", error_msg, None

            # Validate model
            if model_name not in QWEN_CODE_MODELS:
                model_name = DEFAULT_MODEL

            # Prepare messages
            system_message = (
                "You are a helpful assistant analyzing code and files. "
                "Be concise and specific in your responses."
            )
            user_message = f"Here are the files to analyze:\n\n{content}\n\nQuery: {query}"

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]

            # Call API with retry logic for 401 errors
            max_retries = 2

            for attempt in range(max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0,
                        max_tokens=QWEN_CODE_MODELS[model_name]["max_tokens"],
                        stream=True,
                        stream_options={"include_usage": True},
                    )
                    break  # Success, exit retry loop

                except Exception as e:
                    error_str = str(e)

                    # Log the error
                    logger.warning(f"API call attempt {attempt + 1} failed: {error_str}")

                    # If 401 and we have retries left, refresh token and retry
                    if "401" in error_str and attempt < max_retries - 1:
                        logger.info("Got 401, forcing token refresh and retrying...")
                        # Force credential reload and refresh
                        self.credentials = None
                        await self._ensure_authenticated(oauth_path)
                        continue

                    # For other errors or last retry, raise
                    if attempt >= max_retries - 1:
                        logger.error(f"API call failed after {max_retries} attempts: {error_str}")
                        raise

            # Collect response
            full_response = ""
            reasoning_text = ""
            input_tokens = 0
            output_tokens = 0

            async for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        # Check for thinking blocks
                        content_text = delta.content
                        if "<think>" in content_text or "</think>" in content_text:
                            # Simple parsing for thinking blocks
                            parts = content_text.split("<think>")
                            for i, part in enumerate(parts):
                                if "</think>" in part:
                                    think_part, rest = part.split("</think>", 1)
                                    reasoning_text += think_part
                                    full_response += rest
                                elif i == 0:
                                    full_response += part
                                else:
                                    reasoning_text += part
                        else:
                            full_response += content_text

                    # Check for reasoning_content (native reasoning)
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        reasoning_text += delta.reasoning_content

                # Collect usage (tokens tracked by API but not used in response)
                # Usage information available in chunk.usage if needed for monitoring

            # Process response
            processed_response = process_llm_response(full_response)

            # Calculate reasoning tokens (approximate from reasoning text)
            reasoning_tokens = 0
            if reasoning_text:
                # Rough estimate: 4 chars per token
                reasoning_tokens = len(reasoning_text) // 4

            return (
                processed_response,
                None,
                reasoning_tokens if thinking_mode and reasoning_tokens > 0 else None,
            )

        except json.JSONDecodeError as e:
            error_msg = (
                f"JSON decode error: {e}\n"
                f"This usually means the API returned a non-JSON response (HTML error page).\n"
                f"Please check if your OAuth token is valid by re-authenticating."
            )
            logger.error(error_msg)
            return "", error_msg, None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Qwen Code API error: {error_msg}")

            # Provide helpful error messages
            if "401" in error_msg:
                error_msg = (
                    f"Authentication failed: {error_msg}\n"
                    f"Please re-authenticate using Qwen Code OAuth flow."
                )
            elif "Expecting value" in error_msg:
                error_msg = (
                    f"JSON parsing error: {error_msg}\n"
                    f"API returned non-JSON response. Token may be invalid.\n"
                    f"Please re-authenticate."
                )

            return "", error_msg, None
