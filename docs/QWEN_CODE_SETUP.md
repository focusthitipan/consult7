# Qwen Code Provider Setup Guide

## Overview

The Qwen Code provider enables you to use Alibaba Qwen models via OAuth authentication without requiring an API key.

## Prerequisites

1. Have a Qwen account and be authenticated
2. OAuth credentials must be located at `~/.qwen/oauth_creds.json`

## Authentication Setup

### Method 1: Using Qwen Code CLI (Recommended)

```bash
# Install Qwen Code CLI
npm install -g qwen-code-cli

# Authenticate
qwen-code auth login
```

### Method 2: Manual Setup

Create a file at `~/.qwen/oauth_creds.json` with the following structure:

```json
{
  "access_token": "your_access_token",
  "refresh_token": "your_refresh_token",
  "token_type": "Bearer",
  "expiry_date": 1234567890000,
  "resource_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
}
```

## Supported Models

### Via OAuth (2 models)

- `qwen3-coder-plus` - High-performance code analysis (context: 1M, max output: 65k)
- `qwen3-coder-flash` - Fast code analysis optimized for speed (context: 1M, max output: 65k)

### ⚠️ OAuth Limitations

Only **qwen3-coder-plus** and **qwen3-coder-flash** are supported via OAuth.

Other models are **NOT supported via OAuth** (API Key required):
- ❌ `qwen3-max`
- ❌ `qwen-plus`
- ❌ `qwen-flash`
- ❌ `qwen3-vl-plus` (vision model)

## Usage Examples

### Command Line

```bash
# Use default OAuth path (~/.qwen/oauth_creds.json)
consult7 qwen-code oauth:

# Specify custom OAuth path
consult7 qwen-code oauth:~/my-custom-path/oauth_creds.json

# Use qwen3-coder-flash for speed
consult7 qwen-code oauth: --model qwen3-coder-flash

# Test the connection
consult7 qwen-code oauth: --test
```

### MCP Configuration (Claude Desktop)

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

### Python API

```python
from consult7.consultation import consultation_impl

# Use qwen3-coder-plus (default)
result = await consultation_impl(
    files=["/path/to/file.py"],
    query="Review this code",
    model="qwen3-coder-plus",
    mode="fast",
    provider="qwen-code",
    api_key=None  # Use default path: ~/.qwen/oauth_creds.json
)

# Use qwen3-coder-flash for speed
result = await consultation_impl(
    files=["/path/to/file.py"],
    query="Quick code analysis",
    model="qwen3-coder-flash",
    mode="fast",
    provider="qwen-code",
    api_key=None
)
```

## Features

- ✅ OAuth2 authentication (no API key needed)
- ✅ Auto token refresh
- ✅ OpenAI-compatible API
- ✅ Thinking blocks support (`<think>...</think>`)
- ✅ Streaming support
- ✅ Code-focused models

## Troubleshooting

### Authentication Error

```
Error: Failed to load Qwen Code OAuth credentials
```

**Solution**: Verify that the file `~/.qwen/oauth_creds.json` exists and has the correct format

### Token Expired

The system will automatically refresh the token. If refresh fails:

1. Check the `refresh_token` in your credentials file
2. Re-authenticate using Qwen Code CLI

### 401 Unauthorized Error

If the token is expired and refresh fails:

```bash
qwen-code auth logout
qwen-code auth login
```

## Performance Tips

- Use `qwen3-coder-plus` for high-performance code analysis
- Use `qwen3-coder-flash` for quick responses and fast analysis
- Mode `fast` is suitable for quick queries
- Mode `mid` adds reasoning for complex analysis
- Mode `think` is for deep analysis (recommended with coder-plus)

**Note:** If you need to use other models (qwen3-max, qwen-plus, etc.), you must use API Key instead of OAuth

## Cost

Qwen Code OAuth has free and paid tiers - check your quota at the Qwen dashboard
