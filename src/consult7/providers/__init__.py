"""Provider implementations for Consult7."""

from .openrouter import OpenRouterProvider
from .gemini_cli import GeminiCliProvider
from .qwen_code import QwenCodeProvider

# Supported providers
PROVIDERS = {
    "openrouter": OpenRouterProvider(),
    "gemini-cli": GeminiCliProvider(),
    "qwen-code": QwenCodeProvider(),
}

__all__ = ["PROVIDERS", "OpenRouterProvider", "GeminiCliProvider", "QwenCodeProvider"]
