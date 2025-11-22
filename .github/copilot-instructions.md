# Consult7 AI Coding Agent Instructions

## Project Overview
Consult7 is an MCP (Model Context Protocol) server enabling AI agents to consult large context window LLMs for analyzing extensive file collections. **Key characteristic: stateless operation** — each consultation is independent, requiring no shared state between calls.

**Purpose**: Overcome context window limitations by delegating file analysis to capable LLMs via a modular, provider-agnostic architecture.

## Critical Architecture Patterns

### 1. Multi-Provider Architecture (3 Providers)
All providers implement `BaseProvider` interface in `providers/base.py`:

```python
class BaseProvider(ABC):
    async def get_model_info(model_name: str, api_key: Optional[str]) -> Optional[dict]
    async def call_llm(content: str, query: str, model_name: str, api_key: str, 
                       thinking_mode: bool, thinking_budget: Optional[int])
```

**Three registered providers** (in `providers/__init__.py`):
- **openrouter**: 500+ models via API key (production default)
- **gemini-cli**: Google OAuth (free tier, setup in `docs/GEMINI_CLI_SETUP.md`)
- **qwen-code**: Alibaba OAuth (code-focused, setup in `docs/QWEN_CODE_SETUP.md`)

**OAuth path handling** for gemini-cli/qwen-code:
- `oauth:` → default path (`~/.gemini/oauth_creds.json` or `~/.qwen/oauth_creds.json`)
- `oauth:/custom/path.json` → custom path
- In code: `None` = default, string = custom path

### 2. Token Budget Architecture
**Never use hardcoded file limits globally** — always calculate dynamically:

```python
# Step 1: Get model info
model_info = await get_model_context_info(model_name, provider, api_key)
context_length = model_info.get("context_length", DEFAULT_CONTEXT_LENGTH)

# Step 2: Calculate dynamic limits
max_total_size, max_file_size = calculate_max_file_size(context_length, mode, model)
```

**Key distinction**: Reasoning tokens differ by provider:
- **Anthropic/OpenRouter token-based**: Reasoning tokens come FROM `max_tokens` (not additional)
- **Gemini**: Reasoning tokens are ADDITIONAL to output budget
- **OpenAI effort-based**: Uses `effort` levels instead of token counts

Implementation pattern in `providers/openrouter.py` lines 95–125.

### 3. Mode Parameter System (v3.0+)
Structured `mode` enum replaces old `|thinking` suffix:
- `fast`: No reasoning, lowest latency
- `mid`: Moderate reasoning (50% of max thinking budget)
- `think`: Maximum reasoning (full thinking budget)

See `token_utils.py:get_thinking_budget()` for implementation. Model thinking limits defined in `token_utils.py:THINKING_LIMITS`.

### 4. Orchestration Flow (consultation.py)
Main entry point: `consultation_impl()` (stateless function)

```
1. expand_file_patterns() → file_paths, errors
2. get_model_context_info() → model capabilities
3. calculate_max_file_size() → dynamic limits based on model context
4. format_content() → files assembled with limits applied
5. get_thinking_budget() → reasoning budget based on mode
6. call_llm() → invoke provider
7. save_output_to_file() → optional file output
```

## Critical Conventions

### File Pattern Rules (file_processor.py:expand_file_patterns)
- ✅ Wildcards ONLY in filename: `/path/to/dir/*.py`
- ❌ Wildcards in directories: `/path/*/dir/*.py` (invalid)
- ✅ Extension required with wildcards: `*.py` not `*`
- ✅ Absolute paths required
- Default ignore list in `constants.py:DEFAULT_IGNORED`: `__pycache__, .env, secrets.py, .DS_Store, .git, node_modules`

### Error Messages
**All errors must be actionable** with user hints. Example from `file_processor.py`:
```python
errors.append(
    f"Path must be absolute: {pattern}\n"
    f"  Hint: Use absolute paths starting with / (e.g., /Users/name/project/file.py)"
)
```

### Output File Handling
`file_processor.py:save_output_to_file()`:
- If file exists: adds `_updated` suffix (e.g., `report.md` → `report_updated.md`)
- Creates parent directories automatically
- Returns `(actual_path, error_message)` tuple

## Configuration & Constants
**Single source of truth**: `constants.py`
- File size limits: `MAX_FILE_SIZE=1MB`, `MAX_TOTAL_SIZE=4MB`
- API timeouts: `OPENROUTER_TIMEOUT=600s`, `API_FETCH_TIMEOUT=30s`
- Token safety factor: `TOKEN_SAFETY_FACTOR=0.8` (reserves 20% buffer)
- Thinking token limits in `token_utils.py:THINKING_LIMITS`

## MCP Server Integration
`server.py` registers single `consultation` tool with:
- Required params: `files`, `query`, `model`, `mode`
- Optional params: `output_file`, `provider`, `api_key`

CLI usage:
```bash
consult7 openrouter sk-or-v1-your-key [--test]
consult7 gemini-cli oauth: [--test]
consult7 qwen-code oauth: [--test]
```

## Common Pitfalls

1. **Token estimation must include system message** (`providers/openrouter.py:127`)
2. **Don't confuse context length with available input tokens** — always apply safety factor
3. **Reasoning budget must be reserved upfront** before checking token limits
4. **Directory patterns invalid** — only file patterns allowed
5. **Must use absolute paths** — MCP servers run in different working directories
6. **Test API connection** with `--test` flag during development before integration

## Key Files Reference
- `server.py`: MCP server setup, CLI arg parsing, provider selection
- `consultation.py`: Main orchestration (entry point for all operations)
- `file_processor.py`: File discovery and content assembly
- `token_utils.py`: Token estimation, reasoning budget calculation
- `constants.py`: All timeouts, limits, URLs (update here, not scattered)
- `providers/{base,openrouter,gemini_cli,qwen_code}.py`: Provider implementations
- `tool_definitions.py`: Tool schema and model examples (update for UX changes)

## Testing & Validation
```bash
# Install in editable mode
pip install -e .

# Test API connection
consult7 openrouter sk-or-v1-your-key --test
consult7 gemini-cli oauth: --test
consult7 qwen-code oauth: --test

# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/
```

## Development Workflow
1. Modify code
2. Reinstall: `pip install -e .` (already done if installed editable)
3. Test connection: `consult7 <provider> <key> --test`
4. Validate with integration tests
5. Check linting: `ruff check .`
