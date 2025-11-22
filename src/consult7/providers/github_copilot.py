"""GitHub Copilot provider for Consult7.

Implements GitHub Copilot integration using OAuth 2.0 Device Flow
and GitHub Copilot API (OpenAI-compatible format).

Authentication Flow:
1. OAuth Device Flow (RFC 8628) for user authorization
2. Token exchange: OAuth token → Copilot API token
3. Chat completion via OpenAI-compatible endpoint

Reference: AI Gateway implementation (ProxyService.php)
"""

import asyncio
import logging
from typing import Optional, Tuple

import aiohttp

from ..constants import (
    GITHUB_COPILOT_API_TOKEN_URL,
    GITHUB_COPILOT_CLIENT_ID,
    GITHUB_COPILOT_DEVICE_CODE_URL,
    GITHUB_COPILOT_MAX_RETRIES,
    GITHUB_COPILOT_SCOPE,
    GITHUB_COPILOT_TIMEOUT,
    GITHUB_COPILOT_TOKEN_URL,
)
from ..oauth.device_flow import DeviceFlowAuth
from ..oauth.token_storage import TokenStorage
from .base import BaseProvider, process_llm_response

logger = logging.getLogger("consult7")


class GitHubCopilotProvider(BaseProvider):
    """GitHub Copilot provider using OAuth Device Flow + GitHub Copilot API."""

    def __init__(self):
        """Initialize GitHub Copilot provider."""
        self.token_storage = TokenStorage()
        self.device_flow = DeviceFlowAuth(
            client_id=GITHUB_COPILOT_CLIENT_ID,
            device_code_url=GITHUB_COPILOT_DEVICE_CODE_URL,
            token_url=GITHUB_COPILOT_TOKEN_URL,
            scope=GITHUB_COPILOT_SCOPE,
        )

    async def authenticate(self) -> dict:
        """Perform OAuth Device Flow authentication.

        Returns:
            Token data including access_token

        Raises:
            Exception: If authentication fails
        """
        print("\nGitHub Copilot Authentication (Device Flow)")
        print("=" * 60)

        # Step 1: Request device code
        device_info = await self.device_flow.request_device_code(use_pkce=False)

        # Step 2: Display instructions to user
        print(f"\nPlease visit: {device_info['verification_uri']}")
        print(f"Enter code: {device_info['user_code']}")
        print(f"\nCode expires in {device_info['expires_in'] // 60} minutes")
        print("Waiting for authorization...")

        # Step 3: Poll for token
        try:
            logger.info("Polling for GitHub Copilot OAuth token...")
            token_data = await self.device_flow.poll_for_token(
                device_code=device_info["device_code"],
                interval=device_info["interval"],
            )

            # Step 4: Save token
            self.token_storage.save_token("github-copilot", token_data)
            logger.info("GitHub Copilot OAuth token saved successfully")

            print("\n[SUCCESS] Authentication successful!")
            print(f"   Token scope: {token_data['scope']}")
            return token_data

        except Exception as e:
            logger.error(f"GitHub Copilot authentication failed: {e}")
            print(f"\n[FAILED] Authentication failed: {e}")
            raise

    async def get_model_info(self, model_name: str, api_key: Optional[str]) -> Optional[dict]:
        """Get model context information.

        Args:
            model_name: Model name (e.g., 'gpt-4o', 'claude-3.5-sonnet')
            api_key: OAuth token path or 'oauth:' (not used directly)

        Returns:
            Dictionary with model information:
            - context_length: Token context window
            - max_output_tokens: Maximum output tokens
            - provider: 'github-copilot'

        Note:
            GitHub Copilot API doesn't provide model discovery.
            We use hardcoded defaults based on known models.
        """
        # Known model capabilities (GitHub Copilot actual limits in IDE context)
        MODEL_INFO = {
            # GPT-4 Models (Standard Chat)
            "gpt-4o": {"context_length": 128000, "max_output_tokens": 16384},
            "gpt-4.1": {"context_length": 128000, "max_output_tokens": 16384},
            # GPT-5 Models (Base limited for Chat, Mini optimized for speed)
            "gpt-5": {"context_length": 128000, "max_output_tokens": 16384},
            "gpt-5-mini": {"context_length": 128000, "max_output_tokens": 65536},  # High output for fast workloads
            "gpt-5.1": {"context_length": 128000, "max_output_tokens": 16384},
            # Claude Models (Context limited in IDE, but increased output)
            "claude-haiku-4.5": {"context_length": 128000, "max_output_tokens": 16384},
            "claude-sonnet-4": {"context_length": 128000, "max_output_tokens": 16384},
            "claude-sonnet-4.5": {"context_length": 128000, "max_output_tokens": 16384},
            # Gemini Models (Massively reduced context, but high output for agent competition)
            "gemini-2.5-pro": {"context_length": 128000, "max_output_tokens": 65536},
            "gemini-3-pro-preview": {"context_length": 128000, "max_output_tokens": 65536},
            # Grok Models (X AI)
            "grok-code-fast-1": {"context_length": 128000, "max_output_tokens": 10000},
        }

        info = MODEL_INFO.get(model_name, {"context_length": 128000, "max_output_tokens": 16384})

        return {
            "context_length": info["context_length"],
            "max_output_tokens": info["max_output_tokens"],
            "provider": "github-copilot",
        }

    async def _exchange_oauth_token_for_api_token(self, oauth_token: str) -> Tuple[str, str]:
        """Exchange OAuth token for GitHub Copilot API token.

        Args:
            oauth_token: OAuth access token from Device Flow

        Returns:
            Tuple of (api_token, api_endpoint)

        Raises:
            Exception: If token exchange fails
        """
        headers = {
            "Authorization": f"token {oauth_token}",  # Note: 'token' not 'Bearer'
            "Accept": "application/json",
            "User-Agent": "Consult7/3.0",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                GITHUB_COPILOT_API_TOKEN_URL, headers=headers, timeout=30
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(
                        f"Failed to get Copilot API token (HTTP {response.status}).\n"
                        f"  Hint: Re-authenticate with: consult7 github-copilot oauth:\n"
                        f"  Response: {text}"
                    )

                data = await response.json()

                if "token" not in data or "endpoints" not in data:
                    raise Exception(f"Invalid Copilot token response: {data}")

                api_token = data["token"]
                api_endpoint = data["endpoints"]["api"]

                return api_token, api_endpoint

    async def _make_chat_request(
        self,
        api_endpoint: str,
        api_token: str,
        model: str,
        messages: list,
        thinking_budget: Optional[int] = None,
    ) -> dict:
        """Make chat completion request to GitHub Copilot API.

        Args:
            api_endpoint: API base URL
            api_token: Copilot API token
            model: Model name
            messages: List of message dicts
            thinking_budget: Reasoning token budget (for o1 models)

        Returns:
            Chat completion response

        Raises:
            Exception: If request fails
        """
        url = f"{api_endpoint}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_token}",  # Now use 'Bearer'
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Consult7/3.0",
            "Editor-Version": "vscode/1.95.0",
            "Editor-Plugin-Version": "copilot-chat/0.22.4",
            "Openai-Organization": "github-copilot",
            "Openai-Intent": "conversation-panel",
        }

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "intent": True,
            "n": 1,
        }

        # Add reasoning budget for o1 models (if supported)
        if thinking_budget and model.startswith("o1"):
            payload["max_completion_tokens"] = thinking_budget

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=GITHUB_COPILOT_TIMEOUT
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(
                        f"GitHub Copilot API request failed (HTTP {response.status}).\n"
                        f"  Response: {text}"
                    )

                return await response.json()

    async def call_llm(
        self,
        content: str,
        query: str,
        model_name: str,
        api_key: str,
        thinking_mode: bool = False,
        thinking_budget: Optional[int] = None,
    ) -> Tuple[str, Optional[str], Optional[int]]:
        """Call GitHub Copilot and return the response.

        Args:
            content: Formatted file content
            query: User's query
            model_name: Model to use
            api_key: OAuth token path (e.g., 'oauth:' or 'oauth:/path/to/token')
            thinking_mode: Whether thinking/reasoning mode is enabled
            thinking_budget: Number of thinking tokens to use

        Returns:
            Tuple of (response, error_message, actual_thinking_budget_used)
        """
        # Load OAuth token
        token_data = self.token_storage.load_token("github-copilot")

        if not token_data or "access_token" not in token_data:
            return (
                "",
                "No GitHub Copilot token found.\n"
                "  Hint: Authenticate with: consult7 github-copilot oauth:",
                None,
            )

        oauth_token = token_data["access_token"]

        # Prepare messages (OpenAI format)
        system_msg = "You are a code analysis assistant. Analyze the provided files and answer the query accurately and concisely."
        user_msg = f"{content}\n\nQuery: {query}"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        # Retry logic for transient errors
        last_error = None
        logger.info(f"GitHub Copilot: Sending request with model={model_name}, thinking_mode={thinking_mode}")

        for attempt in range(GITHUB_COPILOT_MAX_RETRIES):
            try:
                # Exchange OAuth token for API token
                logger.debug("Exchanging OAuth token for API token...")
                api_token, api_endpoint = await self._exchange_oauth_token_for_api_token(oauth_token)

                # Make chat request
                logger.debug(f"Making chat request to {api_endpoint}")
                response = await self._make_chat_request(
                    api_endpoint=api_endpoint,
                    api_token=api_token,
                    model=model_name,
                    messages=messages,
                    thinking_budget=thinking_budget if thinking_mode else None,
                )

                # Extract response content
                if "choices" not in response or len(response["choices"]) == 0:
                    logger.warning(f"Invalid response format from GitHub Copilot: {response}")
                    return "", f"Invalid response format: {response}", None

                choice = response["choices"][0]
                message = choice.get("message", {})
                response_text = message.get("content", "")

                # Extract actual thinking tokens used (if available)
                usage = response.get("usage", {})
                thinking_used = usage.get("completion_tokens_details", {}).get("reasoning_tokens")

                logger.info(
                    f"GitHub Copilot request successful: model={model_name}, "
                    f"response_length={len(response_text)}, thinking_used={thinking_used}"
                )

                return process_llm_response(response_text), None, thinking_used

            except Exception as e:
                last_error = str(e)
                logger.warning(f"GitHub Copilot request attempt {attempt + 1} failed: {e}")

                # Don't retry on rate limits or auth errors
                if "rate limit" in last_error.lower() or "401" in last_error or "403" in last_error:
                    logger.error(f"GitHub Copilot rate limit or auth error (no retry): {last_error}")
                    return "", last_error, None

                # Retry on transient errors
                if attempt < GITHUB_COPILOT_MAX_RETRIES - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

        return "", f"Request failed after {GITHUB_COPILOT_MAX_RETRIES} attempts: {last_error}", None
