"""Provider implementations for Consult7."""

from .openrouter import OpenRouterProvider
from .gemini_cli import GeminiCliProvider
from .qwen_code import QwenCodeProvider
from .github_copilot import GitHubCopilotProvider

# Supported providers
PROVIDERS = {
    "openrouter": OpenRouterProvider(),
    "gemini-cli": GeminiCliProvider(),
    "qwen-code": QwenCodeProvider(),
    "github-copilot": GitHubCopilotProvider(),
}

__all__ = [
    "PROVIDERS",
    "OpenRouterProvider",
    "GeminiCliProvider",
    "QwenCodeProvider",
    "GitHubCopilotProvider",
]
