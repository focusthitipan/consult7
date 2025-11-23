"""Constants and static configuration for Consult7 MCP server."""

# File size limits
MAX_FILE_SIZE = 1_000_000  # 1MB per file (reasonable for source code files)
MAX_TOTAL_SIZE = 4_000_000  # 4MB total (~1M tokens with 3.5 chars/token)
MAX_RESPONSE_SIZE = 100_000  # 100KB response
FILE_SEPARATOR = "-" * 80

# Default ignored paths
DEFAULT_IGNORED = [
    "__pycache__",
    ".env",
    "secrets.py",
    ".DS_Store",
    ".git",
    "node_modules",
]

# API URLs
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"

# API constants
DEFAULT_TEMPERATURE = 0.7  # Default temperature for all providers
OPENROUTER_TIMEOUT = 600.0  # 10 minutes - very generous timeout for API calls
API_FETCH_TIMEOUT = 30.0  # 30 seconds for fetching model info
DEFAULT_CONTEXT_LENGTH = 128_000  # Default context when not available from API
LLM_CALL_TIMEOUT = 600.0  # 10 minutes - very generous timeout for LLM calls

# Application constants
SERVER_VERSION = "3.0.0"
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
MIN_ARGS = 2  # provider and api-key/oauth-path

# Output token constants
DEFAULT_OUTPUT_TOKENS = 8_000  # Default max output tokens (~300 lines of code)
SMALL_OUTPUT_TOKENS = 4_000  # Output tokens for smaller models
SMALL_MODEL_THRESHOLD = 100_000  # Context size threshold for small models

# GitHub Copilot constants
GITHUB_COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"  # Public client ID for Device Flow
GITHUB_COPILOT_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_COPILOT_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_COPILOT_VERIFICATION_URL = "https://github.com/login/device"
GITHUB_COPILOT_API_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
GITHUB_COPILOT_SCOPE = "read:user copilot"
GITHUB_COPILOT_TIMEOUT = 600.0  # 10 minutes - same as other providers
GITHUB_COPILOT_DEVICE_CODE_EXPIRES_IN = 900  # 15 minutes
GITHUB_COPILOT_POLLING_INTERVAL = 5  # Poll every 5 seconds
GITHUB_COPILOT_MAX_RETRIES = 3  # Max retry attempts for transient errors

# Test model for each provider
TEST_MODELS = {
    "openrouter": "openai/gpt-5.1",
    "gemini-cli": "gemini-2.5-flash",
    "qwen-code": "qwen3-coder-plus",
    "github-copilot": "gpt-4o",
}

# Database constants
DB_QUERY_TIMEOUT = 30.0  # 30 seconds default query timeout
DB_MAX_ROWS = 10_000  # Maximum rows per query result
DB_POOL_SIZE = 5  # Default connection pool size per DSN
DB_SUPPORTED_PROTOCOLS = ["mysql", "postgresql", "sqlite", "mongodb"]
