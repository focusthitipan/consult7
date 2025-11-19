# Consult7 MCP Server

**Consult7** is a Model Context Protocol (MCP) server that enables AI agents to consult large context window models for analyzing extensive file collections - entire codebases, document repositories, or mixed content that exceed the current agent's context limits.

## Supported Providers

Consult7 supports 3 providers:

1. **OpenRouter** - Access to 500+ models via API key
2. **Gemini CLI** - Google Gemini models via OAuth (free tier, no API key needed)
3. **Qwen Code** - Alibaba Qwen models via OAuth (code-focused)

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
claud mcp add -s user consult7-gemini -- consult7 gemini-cli oauth:
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
claud mcp add -s user consult7-qwen -- consult7 qwen-code oauth:
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

### Key Features
- **Code Understanding & Generation** - Query and edit large codebases, generate apps from images/PDFs
- **Automation & Integration** - Automate operational tasks and connect with MCP servers
- **Advanced Capabilities** - Ground queries with Google Search, conversation checkpointing, custom context files
- **GitHub Integration** - Automated PR reviews, issue triage, and workflow automation

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

## Tool Parameters

The consultation tool accepts the following parameters:

- **files** (required): List of absolute file paths or patterns with wildcards in filenames only
- **query** (required): Your question or instruction for the LLM to process the files
- **model** (required): The LLM model to use (see Supported Models above)
- **mode** (required): Performance mode - `fast`, `mid`, or `think`
- **output_file** (optional): Absolute path to save the response to a file instead of returning it
  - If the file exists, it will be saved with `_updated` suffix (e.g., `report.md` → `report_updated.md`)
  - When specified, returns only: `"Result has been saved to /path/to/file"`
  - Useful for generating reports, documentation, or analyses without flooding the agent's context

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

## Testing

```bash
# Test OpenRouter
consult7 openrouter sk-or-v1-your-api-key --test

# Test Gemini CLI
consult7 gemini-cli oauth: --test

# Test Qwen Code
consult7 qwen-code oauth: --test
```

## Uninstalling

To remove consult7 from Claude Code:

```bash
claude mcp remove consult7 -s user
```

## Version History

### v3.0.0
- Removed Google and OpenAI direct providers - now OpenRouter only
- Removed `|thinking` suffix - use `mode` parameter instead (now required)
- Clean `mode` parameter API: `fast`, `mid`, `think`
- Simplified CLI from `consult7 <provider> <key>` to `consult7 <key>`
- Better MCP integration with enum validation for modes
- Dynamic file size limits based on model context window

### v2.1.0
- Added `output_file` parameter to save responses to files

### v2.0.0
- New file list interface with simplified validation
- Reduced file size limits to realistic values

## License

MIT
