# Consult7 MCP Server

**Consult7** is a Model Context Protocol (MCP) server that enables AI agents to consult large context window models for analyzing extensive file collections - entire codebases, document repositories, or mixed content that exceed the current agent's context limits.

## Supported Providers

Consult7 supports 4 providers:

1. **OpenRouter** - Access to 500+ models via API key
2. **Gemini CLI** - Google Gemini models via OAuth (free tier, no API key needed)
3. **Qwen Code** - Alibaba Qwen models via OAuth (code-focused)
4. **GitHub Copilot** - Use your GitHub Copilot subscription via OAuth (no additional API key needed)

## Why Consult7?

**Consult7** enables any MCP-compatible agent to offload file analysis to large context models (up to 2M tokens). Useful when:
- Agent's current context is full
- Task requires specialized model capabilities
- Need to analyze large codebases in a single query
- Want to compare results from different models
- Want to use free OAuth-based providers (Gemini CLI, Qwen Code)

> "For Claude Code users, Consult7 is a game changer."

## How it works

**Consult7** collects files from the specific paths you provide (with optional wildcards in filenames), assembles them into a single context, and sends them to a large context window model along with your query. The result is directly fed back to the agent you are working with.

## Example Use Cases

### Quick codebase summary

* **Files:** `["/Users/john/project/src/*.py", "/Users/john/project/lib/*.py"]`
* **Query:** "Summarize the architecture and main components of this Python project"
* **Model:** `"google/gemini-2.5-flash"`
* **Mode:** `"fast"`

### Deep analysis with reasoning
* **Files:** `["/Users/john/webapp/src/*.py", "/Users/john/webapp/auth/*.py", "/Users/john/webapp/api/*.js"]`
* **Query:** "Analyze the authentication flow across this codebase. Think step by step about security vulnerabilities and suggest improvements"
* **Model:** `"anthropic/claude-sonnet-4.5"`
* **Mode:** `"think"`

### Generate a report saved to file
* **Files:** `["/Users/john/project/src/*.py", "/Users/john/project/tests/*.py"]`
* **Query:** "Generate a comprehensive code review report with architecture analysis, code quality assessment, and improvement recommendations"
* **Model:** `"google/gemini-2.5-pro"`
* **Mode:** `"think"`
* **Output File:** `"/Users/john/reports/code_review.md"`
* **Result:** Returns `"Result has been saved to /Users/john/reports/code_review.md"` instead of flooding the agent's context

## Installation

### Prerequisites

Clone the repository and install locally:

```bash
git clone https://github.com/focusthitipan/consult7.git
cd consult7
pip install -e .
```

### Option 1: OpenRouter (Recommended for most users)

#### Claude Code

```bash
claude mcp add -s user consult7 -- consult7 openrouter your-openrouter-api-key
```

#### Claude Desktop

```json
{
  "mcpServers": {
    "consult7": {
      "type": "stdio",
      "command": "consult7",
      "args": ["openrouter", "your-openrouter-api-key"]
    }
  }
}
```

### Option 2: Gemini CLI (Free, OAuth-based)

**Prerequisites**: Install and authenticate Gemini CLI tool first

```bash
npm install -g @google/generative-ai-cli
gemini  # Login with Google account
```

#### Claude Code

```bash
claude mcp add -s user consult7-gemini -- consult7 gemini-cli oauth:
```

#### Claude Desktop

```json
{
  "mcpServers": {
    "consult7-gemini": {
      "type": "stdio",
      "command": "consult7",
      "args": ["gemini-cli", "oauth:"]
    }
  }
}
```

📖 [Gemini CLI Setup Guide](docs/GEMINI_CLI_SETUP.md)

### Option 3: Qwen Code (OAuth-based, code-focused)

**Prerequisites**: Requires Qwen OAuth credentials (see authentication instructions in [Setup Guide](docs/QWEN_CODE_SETUP.md))

#### Claude Code

```bash
claude mcp add -s user consult7-qwen -- consult7 qwen-code oauth:
```

#### Claude Desktop

```json
{
  "mcpServers": {
    "consult7-qwen": {
      "type": "stdio",
      "command": "consult7",
      "args": ["qwen-code", "oauth:"]
    }
  }
}
```

**Note**: `oauth:` uses default path (`~/.qwen/oauth_creds.json`) automatically. For custom path: `oauth:/path/to/creds.json`

📖 [Qwen Code Setup Guide](docs/QWEN_CODE_SETUP.md)

### Option 4: GitHub Copilot (OAuth-based, subscription required)

**Prerequisites**: 
- Active GitHub Copilot subscription (Individual, Business, or Enterprise) - Check at https://github.com/settings/copilot
- Web browser for one-time authentication

#### Step 1: Authenticate with GitHub

Run the authentication command (first time only):

```bash
consult7 github-copilot oauth: --test
```

**What happens:**
1. System prompts: "Would you like to authenticate now? (yes/no):" → Type `yes`
2. Browser opens automatically to `https://github.com/login/device`
3. Copy the device code shown in terminal (e.g., `ABCD-1234`)
4. Paste code into browser prompt
5. Authorize Consult7 to access your GitHub Copilot
6. Token saved securely to `~/.consult7/github-copilot_oauth_token.enc` (encrypted)

**Note**: Authentication happens once. Subsequent calls use saved token automatically.

#### Step 2: Setup in Claude Code

```bash
claude mcp add -s user consult7-copilot -- consult7 github-copilot oauth:
```

#### Step 3: Setup in Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "consult7-copilot": {
      "type": "stdio",
      "command": "consult7",
      "args": ["github-copilot", "oauth:"]
    }
  }
}
```

**Location:**
- **macOS/Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Step 4: Verify Setup

Test the connection:

```bash
consult7 github-copilot oauth: --test
```

Expected output:
```
✓ OAuth Token found and valid
✓ GitHub Copilot provider is ready
```

📖 [GitHub Copilot Setup Guide](docs/GITHUB_COPILOT_SETUP.md) - Detailed setup, troubleshooting, and advanced usage

---

**Note**: Consult7 requires local installation via `pip install -e .`. Ensure you have cloned the repository and installed the package before use.

## About Qwen Code

**Qwen Code** is a powerful command-line AI workflow tool specifically optimized for [Qwen3-Coder](https://github.com/QwenLM/Qwen3-Coder) models. It's an AI-powered development assistant for your terminal with:

### Key Features
- **Code Understanding & Editing** - Query and edit large codebases beyond traditional context window limits
- **Workflow Automation** - Automate operational tasks like handling pull requests and complex rebases
- **Enhanced Parser** - Adapted parser specifically optimized for Qwen-Coder models
- **Vision Model Support** - Automatically detect images in your input and seamlessly switch to vision-capable models for multimodal analysis
- **Free OAuth Option** - 2,000 requests/day with no token counting needed (Recommended)
- **Session Management** - Control token usage with configurable session limits

### Popular Use Cases
- 📚 Understand new codebases with architecture analysis
- 🔨 Code refactoring & optimization following SOLID principles
- 📝 Generate tests, documentation, and API specifications
- 🚀 Automate development workflows and git operations
- 🐛 Debugging & performance analysis

[🔗 GitHub Repository](https://github.com/QwenLM/qwen-code) | [📖 Documentation](https://qwenlm.github.io/qwen-code-docs/)

## About Gemini CLI

**Gemini CLI** is an open-source AI agent that brings the power of Google's Gemini directly into your terminal. Built by Google, it's designed for developers who live in the command line with:

### Key Features
- **Free Tier** - 60 requests/min and 1,000 requests/day with personal Google account
- **Powerful Gemini 2.5 Pro** - Access to 1M token context window
- **Built-in Tools** - Google Search grounding, file operations, shell commands, web fetching
- **Extensible** - Full MCP (Model Context Protocol) support for custom integrations
- **Terminal-first Design** - Optimized for developers working in the command line
- **GitHub Integration** - Automated PR reviews, issue triage, and on-demand assistance
- **Open Source** - Apache 2.0 licensed with active community
- **Code Understanding & Generation** - Query and edit large codebases, generate apps from images/PDFs
- **Automation & Integration** - Automate operational tasks and connect with MCP servers
- **Advanced Capabilities** - Ground queries with Google Search, conversation checkpointing, custom context files

### Supported Models
- `gemini-2.5-flash` - Fast responses (2s, balanced performance)
- `gemini-2.5-flash-lite` - Ultra fast, lightweight, cost-optimized
- `gemini-2.5-pro` - High quality analysis with reasoning

[🔗 GitHub Repository](https://github.com/google-gemini/gemini-cli) | [📖 Documentation](https://geminicli.com/docs/)

## Command Line Options

### OpenRouter
```bash
consult7 openrouter <api-key> [--test]
```

### Gemini CLI
```bash
consult7 gemini-cli oauth: [--test]                    # Use default path: ~/.gemini/oauth_creds.json
consult7 gemini-cli oauth:/custom/path.json [--test]   # Use custom path
```

### Qwen Code
```bash
consult7 qwen-code oauth: [--test]                     # Use default path: ~/.qwen/oauth_creds.json
consult7 qwen-code oauth:/custom/path.json [--test]    # Use custom path
```

### GitHub Copilot
```bash
consult7 github-copilot oauth: [--test]                # Use default path: ~/.consult7/github-copilot_oauth_token.enc
consult7 github-copilot oauth:/custom/path.enc [--test] # Use custom path
```

**Options:**
- `--test`: Test the provider connection
- `oauth:` uses default path automatically
- `oauth:/path/to/file` specifies custom path

## Supported Models

### OpenRouter (500+ models available)

Flagship models with optimized dynamic file size limits:

| Model | Context | Use Case |
|-------|---------|----------|
| `openai/gpt-5.1` | 400k | Latest GPT, balanced performance |
| `google/gemini-2.5-pro` | 1M | Best for complex analysis |
| `google/gemini-2.5-flash` | 1M | Fast, good for most tasks |
| `google/gemini-2.5-flash-lite` | 1M | Ultra fast, simple queries |
| `anthropic/claude-sonnet-4.5` | 1M | Excellent reasoning |
| `anthropic/claude-opus-4.1` | 200k | Best quality, slower |
| `x-ai/grok-4` | 256k | Alternative reasoning model |
| `x-ai/grok-4-fast` | 2M | Largest context window |

You can use any OpenRouter model ID (e.g., `deepseek/deepseek-r1-0528`). See the [full model list](https://openrouter.ai/models). File size limits are automatically calculated based on each model's context window.

### Gemini CLI (OAuth, Free)

| Model | Context | Max Output | Use Case |
|-------|---------|------------|----------|
| `gemini-2.5-flash` | 1.048M | 64k | Fast responses (2s, balanced performance, free tier) |
| `gemini-2.5-flash-lite` | 1.048M | 64k | Ultra fast, lightweight, cost-optimized (free tier) |
| `gemini-2.5-pro` | 1.048M | 64k | High quality analysis with reasoning (free tier) |

**Note**: Only Gemini 2.5 Series supported (1.5 and 1.0 not supported via OAuth)

### Qwen Code (OAuth, Code-focused)

| Model | Context | Max Output | Use Case |
|-------|---------|------------|----------|
| `qwen3-coder-plus` | 1M | 65k | High-performance code analysis (OAuth) |
| `qwen3-coder-flash` | 1M | 65k | Fast code analysis optimized for speed (OAuth) |

**Note**: Other Qwen models require API Key instead of OAuth

### GitHub Copilot (OAuth, Subscription required)

**GPT Models:**
| Model | Context | Max Output | Use Case |
|-------|---------|------------|----------|
| `gpt-4o` | 128k | 16k | Balanced performance, good for most tasks |
| `gpt-4.1` | 128k | 16k | Latest GPT-4 model |
| `gpt-5` | 128k | 16k | Latest GPT-5 model |
| `gpt-5-mini` | 128k | 64k | Fast, cost-effective |
| `gpt-5.1` | 128k | 16k | Cutting edge GPT-5 |

**Claude Models:**
| Model | Context | Max Output | Use Case |
|-------|---------|------------|----------|
| `claude-haiku-4.5` | 128k* | 16k* | Fast, efficient Claude model |
| `claude-sonnet-4` | 128k* | 16k* | Balanced reasoning and performance |
| `claude-sonnet-4.5` | 128k* | 16k* | Excellent reasoning and analysis |

**Gemini Models:**
| Model | Context | Max Output | Use Case |
|-------|---------|------------|----------|
| `gemini-2.5-pro` | 128k* | 64k* | High-quality analysis |
| `gemini-3-pro-preview` | 128k* | 64k* | Preview model with improvements |

**X AI Models:**
| Model | Context | Max Output | Use Case |
|-------|---------|------------|----------|
| `grok-code-fast-1` | 128k | 10k | Optimized output tokens |

**\*Note**: Claude and Gemini models show reduced context/output limits in GitHub Copilot IDE integration compared to their nominal API capabilities. See [Setup Guide](docs/GITHUB_COPILOT_SETUP.md) for details.

## Performance Modes

- **`fast`**: No reasoning - quick answers, simple tasks
- **`mid`**: Moderate reasoning - code reviews, bug analysis
- **`think`**: Maximum reasoning - security audits, complex refactoring

## File Specification Rules

- **Absolute paths only**: `/Users/john/project/src/*.py`
- **Wildcards in filenames only**: `/Users/john/project/*.py` (not in directory paths)
- **Extension required with wildcards**: `*.py` not `*`
- **Mix files and patterns**: `["/path/src/*.py", "/path/README.md", "/path/tests/*_test.py"]`

**Common patterns:**
- All Python files: `/path/to/dir/*.py`
- Test files: `/path/to/tests/*_test.py` or `/path/to/tests/test_*.py`
- Multiple extensions: `["/path/*.js", "/path/*.ts"]`

**Automatically ignored:** `__pycache__`, `.env`, `secrets.py`, `.DS_Store`, `.git`, `node_modules`

**Size limits:** Dynamic based on model context window (e.g., Grok 4 Fast: ~8MB, GPT-5.1: ~1.5MB)

## Hybrid Consultation: Files + Database ✨ NEW

Consult7 now supports **analyzing files and database queries together** in a single consultation! This enables comprehensive analysis of code-database relationships:

```json
{
  "files": ["/Users/john/project/src/**/*.ts"],
  "db_queries": ["SHOW TABLES;", "DESCRIBE users;"],
  "db_dsn": "mysql://root:password@localhost:3306/myapp",
  "query": "Check if the User model matches the database schema",
  "model": "google/gemini-2.5-pro",
  "mode": "think"
}
```

### Configuration via MCP Settings

You can configure the database DSN in your MCP configuration to avoid passing it in every request:

**Claude Code:**
```bash
claude mcp add -s user consult7 -- consult7 openrouter your-api-key --db-dsn mysql://root:password@localhost:3306/myapp
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "consult7": {
      "type": "stdio",
      "command": "consult7",
      "args": [
        "openrouter",
        "your-openrouter-api-key",
        "--db-dsn",
        "mysql://root:password@localhost:3306/myapp"
      ]
    }
  }
}
```

**Cursor** (`mcp_settings.json`):
```json
{
  "mcpServers": {
    "consult7": {
      "command": "consult7",
      "args": [
        "openrouter",
        "your-openrouter-api-key",
        "--db-dsn",
        "mysql://root:password@localhost:3306/myapp"
      ]
    }
  }
}
```

**VS Code Copilot** (`settings.json`):
```json
{
  "github.copilot.chat.mcp.servers": {
    "consult7": {
      "command": "consult7",
      "args": [
        "openrouter",
        "your-openrouter-api-key",
        "--db-dsn",
        "mysql://root:password@localhost:3306/myapp"
      ]
    }
  }
}
```

**Note on DSN Format:** 
- **MySQL/PostgreSQL with password**: `mysql://user:password@host:port/database` (e.g., `mysql://root:mypass@localhost:3306/myapp`)
- **MySQL/PostgreSQL without password**: `mysql://user:@host:port/database` (e.g., `mysql://root:@localhost:3306/myapp`) - note the colon after username
- **SQLite**: File path required (e.g., `sqlite:///./path/to/database.db`)
- **MongoDB with database**: `mongodb://user:password@host:port/database` (e.g., `mongodb://root:pass@localhost:27017/myapp`)
- **MongoDB without database**: `mongodb://user:password@host:port` (e.g., `mongodb://root:pass@localhost:27017`)

**Note on Database Selection:**
- **DSN with database** (e.g., `mysql://root:@localhost:3306/myapp`): Database is automatically selected. Do NOT use `USE database;` in queries.
- **DSN without database** (e.g., `mysql://root:@localhost:3306`): 
  - MySQL/MariaDB: First query must be `USE database_name;`
  - PostgreSQL: First query must be `\c database_name` OR add database to DSN
  - MongoDB: Database MUST be in DSN (cannot be selected via query)
  - SQLite: Database is the file path in DSN (no selection needed)

**With MCP configuration set**, you can omit `db_dsn` parameter:
```json
{
  "files": ["/Users/john/project/src/**/*.ts"],
  "db_queries": ["SHOW TABLES;", "DESCRIBE users;"],
  "query": "Check if the User model matches the database schema",
  "model": "google/gemini-2.5-pro",
  "mode": "think"
}
```

**Supported Databases:**
- ✅ MySQL / MariaDB / TiDB (via `mysql://` DSN)
- ✅ PostgreSQL / CockroachDB (via `postgresql://` DSN)
- ✅ SQLite (via `sqlite:///` DSN)
- ✅ MongoDB (via `mongodb://` DSN)

**Use Cases:**
- Validate ORM models against database schema
- Analyze data patterns with business logic
- Review API implementations with database design
- Assess migration impact on code
- Generate comprehensive code+database documentation

**Test Coverage:** 196/196 tests passing (100% coverage) including MySQL, PostgreSQL, SQLite, and MongoDB integration tests.

📖 [Hybrid Consultation Guide](docs/HYBRID_CONSULTATION_FEATURE.md) - Complete feature documentation with examples

## Tool Parameters

The consultation tool accepts the following parameters:

**File Analysis (Original Mode):**
- **files** (required): List of absolute file paths or patterns with wildcards in filenames only
- **query** (required): Your question or instruction for the LLM to process the files
- **model** (required): The LLM model to use (see Supported Models above)
- **mode** (required): Performance mode - `fast`, `mid`, or `think`
- **output_file** (optional): Absolute path to save the response to a file instead of returning it
  - If the file exists, it will be saved with `_updated` suffix (e.g., `report.md` → `report_updated.md`)
  - When specified, returns only: `"Result has been saved to /path/to/file"`
  - Useful for generating reports, documentation, or analyses without flooding the agent's context

**Database Analysis (New):**
- **db_queries** (optional): List of SQL/MongoDB queries to execute (read-only, SELECT/SHOW/DESCRIBE only)
- **db_dsn** (optional): Database connection string (format: `mysql://user:pass@host:port/database`)
  - Required if `db_queries` is provided
  - Supports: MySQL, PostgreSQL, SQLite, MongoDB

**Modes:**
- **Files Only**: Provide `files` parameter (existing behavior, fully backward compatible)
- **Database Only**: Provide `db_queries` + `db_dsn` parameters (new)
- **Hybrid**: Provide `files` + `db_queries` + `db_dsn` parameters (new)

## Usage Examples

### Via MCP in Claude Code

Claude Code will automatically use the tool with proper parameters:

```json
{
  "files": ["/Users/john/project/src/*.py"],
  "query": "Explain the main architecture",
  "model": "google/gemini-2.5-flash",
  "mode": "mid"
}
```

### Via Python API

**OpenRouter:**
```python
from consult7.consultation import consultation_impl

result = await consultation_impl(
    files=["/path/to/file.py"],
    query="Explain this code",
    model="google/gemini-2.5-flash",
    mode="mid",
    provider="openrouter",
    api_key="sk-or-v1-..."
)
```

**Gemini CLI:**
```python
result = await consultation_impl(
    files=["/path/to/file.py"],
    query="Explain this code",
    model="gemini-2.5-flash",
    mode="mid",
    provider="gemini-cli",
    api_key=None  # Use default path: ~/.gemini/oauth_creds.json
    # or api_key="/custom/path/oauth_creds.json" for custom path
)
```

**Qwen Code:**
```python
result = await consultation_impl(
    files=["/path/to/file.py"],
    query="Review this code",
    model="qwen3-coder-plus",
    mode="fast",
    provider="qwen-code",
    api_key=None  # Use default path: ~/.qwen/oauth_creds.json
    # or api_key="/custom/path/oauth_creds.json" for custom path
)
```

**GitHub Copilot:**
```python
result = await consultation_impl(
    files=["/path/to/file.py"],
    query="Analyze this code",
    model="gpt-4o",
    mode="mid",
    provider="github-copilot",
    api_key=None  # Use default path: ~/.consult7/github-copilot_oauth_token.enc
    # or api_key="/custom/path/token.enc" for custom path
)
```

### Via MCP in Claude Code (GitHub Copilot Example)

Once authenticated and setup, you can use Consult7 directly in Claude Code:

```json
{
  "files": ["/Users/john/project/src/*.py", "/Users/john/project/lib/*.py"],
  "query": "Analyze the architecture and identify potential security vulnerabilities",
  "model": "gpt-4o",
  "mode": "think"
}
```

**Available GitHub Copilot Models:**
- `gpt-4o`, `gpt-4.1`, `gpt-5`, `gpt-5-mini`, `gpt-5.1` (GPT series)
- `claude-haiku-4.5`, `claude-sonnet-4`, `claude-sonnet-4.5` (Claude series)
- `gemini-2.5-pro`, `gemini-3-pro-preview` (Gemini series)
- `grok-code-fast-1` (X AI models)

**Recommended Modes:**
- `fast` - Quick analysis, summarization
- `mid` - Code reviews, bug detection
- `think` - Deep security analysis, complex refactoring, architectural decisions

## Testing

```bash
# Test OpenRouter
consult7 openrouter sk-or-v1-your-api-key --test

# Test Gemini CLI
consult7 gemini-cli oauth: --test

# Test Qwen Code
consult7 qwen-code oauth: --test

# Test GitHub Copilot
consult7 github-copilot oauth: --test
```

## Troubleshooting GitHub Copilot

### "OAuth Token not found" error

**Solution**: Authenticate first using the test command:
```bash
consult7 github-copilot oauth: --test
```

Then follow the interactive OAuth Device Flow to authorize.

### "No GitHub Copilot subscription found" error

**Check your subscription**:
1. Visit https://github.com/settings/copilot
2. Ensure your subscription is active (not expired)
3. Verify you're using the correct GitHub account
4. Try re-authenticating:
   ```bash
   rm ~/.consult7/github-copilot_oauth_token.enc
   consult7 github-copilot oauth: --test
   ```

### Browser doesn't open automatically

**Manual steps**:
1. Copy the device code from terminal (e.g., `ABCD-1234`)
2. Manually visit https://github.com/login/device
3. Paste code and authorize
4. Wait for confirmation in terminal

### Still having issues?

📖 See [GitHub Copilot Setup Guide](docs/GITHUB_COPILOT_SETUP.md) for detailed troubleshooting and advanced configuration.

## Uninstalling

To remove consult7 from Claude Code:

```bash
claude mcp remove consult7 -s user
```

## License

MIT
