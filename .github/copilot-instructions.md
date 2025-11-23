# Consult7 AI Coding Agent Instructions

## Project Overview
Consult7 is an MCP (Model Context Protocol) server enabling AI agents to consult large context window LLMs for analyzing extensive file collections. **Key characteristic: stateless operation** — each consultation is independent, requiring no shared state between calls.

**Purpose**: Overcome context window limitations by delegating file analysis to capable LLMs via a modular, provider-agnostic architecture.

## Critical Architecture Patterns

### 1. Multi-Provider Architecture (4 Providers)
All providers implement `BaseProvider` interface in `providers/base.py`:

```python
class BaseProvider(ABC):
    async def get_model_info(model_name: str, api_key: Optional[str]) -> Optional[dict]
    async def call_llm(content: str, query: str, model_name: str, api_key: str, 
                       thinking_mode: bool, thinking_budget: Optional[int])
```

**Four registered providers** (in `providers/__init__.py`):
- **openrouter**: 500+ models via API key (production default)
- **gemini-cli**: Google OAuth (free tier, setup in `docs/GEMINI_CLI_SETUP.md`)
- **qwen-code**: Alibaba OAuth (code-focused, setup in `docs/QWEN_CODE_SETUP.md`)
- **github-copilot**: GitHub OAuth (subscription required, setup in `docs/GITHUB_COPILOT_SETUP.md`)

**OAuth path handling** for gemini-cli/qwen-code/github-copilot:
- `oauth:` → default path (`~/.gemini/oauth_creds.json`, `~/.qwen/oauth_creds.json`, or `~/.consult7/github-copilot_oauth_token.enc`)
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
- Token safety factor: `TOKEN_SAFETY_FACTOR=0.9` (reserves 10% buffer)
- Thinking token limits in `token_utils.py:THINKING_LIMITS`
- Database constants: `DB_QUERY_TIMEOUT=30s`, `DB_MAX_ROWS=10,000`, `DB_POOL_SIZE=5`

## Hybrid Consultation: Files + Database (v3.0+)

### Overview
Consult7 supports **analyzing files and database queries together** in a single consultation. This enables comprehensive analysis of code-database relationships.

### Supported Databases
- ✅ **MySQL/MariaDB/TiDB**: `mysql://user:pass@host:port/database`
- ✅ **PostgreSQL/CockroachDB**: `postgresql://user:pass@host:port/database`
- ✅ **SQLite**: `sqlite:///./path/to/database.db`
- ✅ **MongoDB**: `mongodb://user:pass@host:port/database`

### Database Adapter Architecture
All adapters in `src/consult7/database/adapters/` implement `BaseAdapter` interface:

```python
class BaseAdapter(ABC):
    @property
    @abstractmethod
    def dsn(self) -> str:
        """Return DSN for logging (format: protocol://[user@]host:port/database)"""
        pass
    
    @abstractmethod
    def connect(self) -> None:
        """Establish database connection"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute read-only query and return results"""
        pass
    
    @abstractmethod
    def format_result(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format results as readable text"""
        pass
```

**Critical adapter patterns:**
1. **DSN property for logging**: All adapters must implement `@property dsn` returning formatted connection string
2. **Read-only enforcement**: Queries are validated before execution, write operations blocked
3. **Consistent logging**: Use `dsn=self.dsn` parameter in `log_query_execution()` calls
4. **Boolean checks for database objects**: Use `if self.database is None` not `if not self.database` (pymongo objects don't support truthiness)
5. **Max rows limit**: All queries respect `max_rows` parameter to prevent token overflow

### MongoDB Adapter Specifics
MongoDB adapter (`mongodb.py`) uses **simplified query parser** for security:
- ✅ Supports: `collection.find()`, `collection.aggregate()`
- ❌ Does NOT parse: filter parameters, projections, sort operations
- Implementation: Always executes `collection.find().limit(max_rows)`
- Rationale: Avoids `eval()` risks while maintaining read-only safety

### Tool Parameters (Updated)
**File-only mode (backward compatible):**
- `files` (required): List of absolute file paths or patterns
- `query` (required): Analysis question
- `model` (required): Model name
- `mode` (required): `fast`, `mid`, or `think`

**Database-only mode:**
- `db_queries` (required): List of SQL/MongoDB queries (read-only)
- `db_dsn` (optional): Database connection string (can use environment variables if not provided)
- `query` (required): Analysis question
- `model` (required): Model name
- `mode` (required): `fast`, `mid`, or `think`

**Hybrid mode:**
- `files` (required): File paths/patterns
- `db_queries` (required): Database queries
- `db_dsn` (optional): Database connection string (can use environment variables if not provided)
- `query` (required): Analysis question
- `model` (required): Model name
- `mode` (required): `fast`, `mid`, or `think`

### Token Budget with Database
Database results are included in token budget calculation:

```python
# File content tokens
file_tokens = estimate_tokens(formatted_files)

# Database result tokens
db_tokens = estimate_tokens(formatted_db_results)

# Total input tokens
total_input_tokens = file_tokens + db_tokens

# Must fit within: (context_length - thinking_budget - output_reserve) * safety_factor
```

If combined content exceeds budget, database results are truncated first.

### Test Coverage
- **Unit tests**: 119 tests (consultation modes, DSN parsing, validation, formatting, token budget)
- **Integration tests**: 77 tests across 4 databases
  - MySQL: 19 tests (connection, queries, read-only, formatting, timeouts, edge cases)
  - PostgreSQL: 19 tests (same coverage as MySQL)
  - SQLite: 19 tests (in-memory + file-based connections)
  - MongoDB: 20 tests (including nested docs, unicode, arrays)
- **Total**: 196/196 tests passing (100%)

## MCP Server Integration
`server.py` registers single `consultation` tool with:
- Required params: `query`, `model`, `mode`
- Optional params: `files`, `output_file`, `db_queries`, `db_dsn`, `db_timeout`, `db_max_rows`

CLI usage:
```bash
consult7 openrouter sk-or-v1-your-key [--test]
consult7 gemini-cli oauth: [--test]
consult7 qwen-code oauth: [--test]
consult7 github-copilot oauth: [--test]
```

## Common Pitfalls

1. **Token estimation must include system message** (`providers/openrouter.py:127`)
2. **Don't confuse context length with available input tokens** — always apply safety factor
3. **Reasoning budget must be reserved upfront** before checking token limits
4. **Directory patterns invalid** — only file patterns allowed
5. **Must use absolute paths** — MCP servers run in different working directories
6. **Test API connection** with `--test` flag during development before integration
7. **Database DSN is now optional** — can fall back to environment variables (see `consultation.py`)

## Key Files Reference
- `server.py`: MCP server setup, CLI arg parsing, provider selection
- `consultation.py`: Main orchestration (entry point for all operations)
- `file_processor.py`: File discovery and content assembly
- `token_utils.py`: Token estimation, reasoning budget calculation
- `constants.py`: All timeouts, limits, URLs (update here, not scattered)
- `providers/{base,openrouter,gemini_cli,qwen_code,github_copilot}.py`: Provider implementations
- `tool_definitions.py`: Tool schema and model examples (update for UX changes)
- `database/adapters/{base,mysql,postgresql,sqlite,mongodb}.py`: Database adapter implementations
- `database/{connection,validation,formatting,token_budget}.py`: Database feature modules

## Testing & Validation
```bash
# Install in editable mode
pip install -e .

# Test API connection
consult7 openrouter sk-or-v1-your-key --test
consult7 gemini-cli oauth: --test
consult7 qwen-code oauth: --test
consult7 github-copilot oauth: --test

# Run all tests (196 tests)
pytest tests/ -v

# Run unit tests only (119 tests)
pytest tests/unit/ -v

# Run integration tests only (77 tests)
pytest tests/integration/ -v

# Run specific database tests
pytest tests/integration/test_mysql_integration.py -v
pytest tests/integration/test_postgresql_integration.py -v
pytest tests/integration/test_sqlite_integration.py -v
pytest tests/integration/test_mongodb_integration.py -v
```

## Development Workflow
1. Modify code
2. Reinstall: `pip install -e .` (already done if installed editable)
3. Test connection: `consult7 <provider> <key> --test`
4. Validate with integration tests
5. Check linting: `ruff check .`

## Project Structure
```
src/consult7/
├── __init__.py           # Package initialization
├── __main__.py           # Entry point
├── server.py             # MCP server (CLI parsing, tool registration)
├── consultation.py       # Main orchestration logic
├── file_processor.py     # File pattern expansion & formatting
├── token_utils.py        # Token estimation & thinking budgets
├── constants.py          # Configuration constants
├── tool_definitions.py   # Tool schema definitions
├── providers/            # LLM provider implementations
│   ├── base.py          # BaseProvider interface
│   ├── openrouter.py    # OpenRouter (500+ models)
│   ├── gemini_cli.py    # Google Gemini OAuth
│   ├── qwen_code.py     # Alibaba Qwen OAuth
│   └── github_copilot.py # GitHub Copilot OAuth
├── database/             # Database integration (v3.0+)
│   ├── connection.py    # Connection pooling & DSN parsing
│   ├── validation.py    # Read-only query validation
│   ├── formatting.py    # Result formatting for LLMs
│   └── adapters/        # Database-specific implementations
│       ├── base.py      # BaseAdapter interface
│       ├── mysql.py     # MySQL/MariaDB/TiDB
│       ├── postgresql.py # PostgreSQL/CockroachDB
│       ├── sqlite.py    # SQLite
│       └── mongodb.py   # MongoDB
└── oauth/                # OAuth authentication
    ├── device_flow.py   # OAuth Device Flow implementation
    └── token_storage.py # Secure token storage (AES-256-GCM)
```
