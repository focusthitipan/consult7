# Consult7 AI Coding Agent Instructions

## Project Overview
Consult7 is an MCP (Model Context Protocol) server that enables AI agents to consult large context window models for analyzing extensive file collections. Key characteristic: **stateless operation** - each consultation call is independent.

**Architecture**: Simple modular pipeline with clear separation of concerns
- `server.py`: MCP server setup, CLI arg parsing (supports 3 providers), tool registration
- `consultation.py`: Orchestrates file processing → model info fetching → API call → response formatting
- `file_processor.py`: File discovery with glob patterns, content assembly, output file handling
- `providers/`: LLM provider abstraction layer
  - `base.py`: Abstract base class defining provider interface
  - `openrouter.py`: 500+ models via API key (production-ready)
  - `gemini_cli.py`: Google OAuth-based access (free tier)
  - `qwen_code.py`: Alibaba OAuth-based access (code-focused)
- `token_utils.py`: Token estimation and reasoning budget calculations
- `tool_definitions.py`: MCP tool schema, descriptions, and model examples
- `constants.py`: Single source of truth for all timeouts, limits, URLs

## Critical Conventions

### 1. Multi-Provider Architecture
**Three provider system** with unified interface via `base.py`:
```python
# All providers must implement BaseProvider interface
class MyProvider(BaseProvider):
    async def get_model_info(self, model_name: str, api_key: Optional[str]) -> Optional[dict]:
        """Return dict with context_length, max_output_tokens, provider"""
        
    async def call_llm(self, content: str, query: str, model_name: str, 
                       api_key: str, thinking_mode: bool, thinking_budget: Optional[int]):
        """Return tuple: (response, error, thinking_budget_used)"""
```

**Provider registration** in `providers/__init__.py`:
```python
PROVIDERS = {
    "openrouter": OpenRouterProvider(),
    "gemini-cli": GeminiCLIProvider(),
    "qwen-code": QwenCodeProvider(),
}
```

**OAuth path handling** for gemini-cli/qwen-code:
- `oauth:` → uses default path (`~/.gemini/oauth_creds.json` or `~/.qwen/oauth_creds.json`)
- `oauth:/custom/path.json` → uses custom path
- In code: `None` means "use default path", string means "custom path"

### 2. Token Budget Architecture
**Dynamic file limits based on model context**. Never use hardcoded limits globally:
```python
# Get model info first
model_info = await get_model_context_info(model_name, provider, api_key)
context_length = model_info.get("context_length", DEFAULT_CONTEXT_LENGTH)

# Calculate dynamic limits
max_total_size, max_file_size = calculate_max_file_size(context_length, mode, model)
```

**Reasoning token handling varies by provider**:
- **Anthropic**: Reasoning tokens come FROM `max_tokens` (not additional)
- **Gemini**: Reasoning tokens are ADDITIONAL to output budget
- **OpenAI**: Uses `effort` levels instead of token counts

See `providers/openrouter.py` lines 95-125 for the complete implementation pattern.

### 3. Error Messages Must Be Actionable
Always include hints for users. Example from `file_processor.py`:
```python
errors.append(
    f"Path must be absolute: {pattern}\n"
    f"  Hint: Use absolute paths starting with / (e.g., /Users/name/project/file.py)"
)
```

### 4. File Pattern Validation Rules
From `file_processor.py:expand_file_patterns()`:
- Wildcards ONLY in filename portion (not in directories)
- Extension MUST be specified with wildcards (`*.py` not `*`)
- Absolute paths required
- Default ignore list in `constants.py:DEFAULT_IGNORED`

### 5. Mode Parameter System (v3.0+)
Replaced `|thinking` suffix with structured `mode` enum:
- `fast`: No reasoning, lowest latency
- `mid`: Moderate reasoning (50% of max thinking budget)
- `think`: Maximum reasoning (full thinking budget)

**Implementation in `token_utils.py:get_thinking_budget()`**:
```python
def get_thinking_budget(model_name: str, mode: str) -> Optional[int]:
    if mode == "fast":
        return None
    limit = THINKING_LIMITS.get(model_name)
    if limit == "effort":  # OpenAI models
        return "effort"
    if mode == "mid":
        return limit // 2
    if mode == "think":
        return limit
```

## Development Workflows

### Prerequisites

First, install the package locally:

```powershell
# Clone and install in editable mode
git clone https://github.com/focusthitipan/consult7.git
cd consult7
pip install -e .
```

### Testing API Connection
```powershell
# Windows PowerShell
# OpenRouter
consult7 openrouter sk-or-v1-your-key --test

# Gemini CLI (OAuth)
consult7 gemini-cli oauth: --test

# Qwen Code (OAuth)
consult7 qwen-code oauth: --test
```

### Running Locally During Development
```powershell
# Install in editable mode
pip install -e .

# Run with test flag (OpenRouter)
consult7 openrouter sk-or-v1-your-key --test

# Or test via Python module
python -m consult7 openrouter sk-or-v1-your-key --test

# Test OAuth providers
consult7 gemini-cli oauth: --test
consult7 qwen-code oauth: --test
```

### Adding New Models
Only modify `token_utils.py:THINKING_LIMITS` for officially supported models:
```python
THINKING_LIMITS = {
    "provider/model-name": 32000,  # Token-based reasoning
    "openai/gpt-5.1": "effort",    # Effort-based reasoning
}
```

All 500+ OpenRouter models work automatically, but only add thinking limits for tested flagship models.

### Linting
Project uses Ruff (configured in `pyproject.toml`):
```powershell
ruff check .
ruff format .
```

**Note**: Print statements allowed in `server.py` (for CLI) and test files.

## Integration Points

### MCP Protocol
Uses `mcp>=1.9.4` library. Tool registration pattern in `server.py`:
```python
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name="consultation", ...)]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    result = await consultation_impl(...)
    return [types.TextContent(type="text", text=result)]
```

### OpenRouter API
Single provider implementation in `providers/openrouter.py`:
- Fetches model info from `/api/v1/models` endpoint
- Handles 3 reasoning modes: token-based, effort-based, none
- 10-minute timeout (`OPENROUTER_TIMEOUT = 600.0`)
- Requires headers: `Authorization`, `HTTP-Referer`, `X-Title`

### OAuth Providers (Gemini CLI & Qwen Code)
OAuth-based providers in `providers/gemini_cli.py` and `providers/qwen_code.py`:
- Use Google/Alibaba OAuth for authentication (no API key needed)
- Credentials stored in `~/.gemini/oauth_creds.json` or `~/.qwen/oauth_creds.json`
- Custom paths supported via `oauth:/custom/path.json` syntax
- Free tier access for development and testing
- See `docs/GEMINI_CLI_SETUP.md` and `docs/QWEN_CODE_SETUP.md` for setup details

### Output File Handling
`file_processor.py:save_output_to_file()` has conflict resolution:
- If file exists: adds `_updated` suffix
- Creates parent directories automatically
- Returns `(actual_path, error_message)` tuple

## Common Pitfalls

1. **Token estimation must include system message**: See `providers/openrouter.py:127`
   ```python
   total_input = system_msg + user_msg
   estimated_tokens = estimate_tokens(total_input)
   ```

2. **Don't confuse context length with available input tokens**:
   ```python
   available_for_input = int((context_length - max_output_tokens) * TOKEN_SAFETY_FACTOR)
   ```

3. **Reasoning budget must be reserved upfront** before checking token limits (see `providers/openrouter.py:152-163`)

4. **Directory patterns are invalid** - only file patterns allowed:
   ```
   ✓ /path/to/dir/*.py
   ✗ /path/*/dir/*.py
   ```

5. **Always use absolute paths** - MCP servers run in different working directories

## Key Files Reference
- `constants.py`: All timeouts, limits, URLs (single source of truth)
- `tool_definitions.py`: Model examples and tool descriptions (update for UX changes)
- `consultation.py:consultation_impl()`: Main orchestration - good starting point for flow
- `providers/openrouter.py`: Study this for reasoning mode handling patterns

## Version Context
Current: v3.0.0 (multi-provider, mode enum system)
Previous: v2.x (multi-provider, `|thinking` suffix)
See `RELEASE_NOTES_v3.0.0.md` for migration context.
