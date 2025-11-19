# Gemini CLI Provider Setup Guide

## Overview

The Gemini CLI provider enables you to use Google Gemini models via OAuth authentication without requiring an API key.

## Prerequisites

1. Install the Gemini CLI tool:
   ```bash
   npm install -g @google/generative-ai-cli
   ```

2. Authenticate with your Google account:
   ```bash
   gemini
   ```
   - The system will open a browser for you to log in with Google
   - Credentials will be saved at `~/.gemini/oauth_creds.json`

## Supported Models

- `gemini-2.5-flash` - Fast responses (context: 1.048M, max output: 64k, free tier)
- `gemini-2.5-flash-lite` - Ultra fast, lightweight, cost-optimized (context: 1.048M, max output: 64k, free tier)
- `gemini-2.5-pro` - High quality analysis with reasoning (context: 1.048M, max output: 64k, free tier)

### ⚠️ OAuth Limitations

Only **Gemini 2.5 Series** is supported:
- ✅ `gemini-2.5-flash`
- ✅ `gemini-2.5-flash-lite`
- ✅ `gemini-2.5-pro`

Models that are **NOT supported** (HTTP 404):
- ❌ `gemini-1.5-pro`
- ❌ `gemini-1.5-flash`
- ❌ `gemini-1.0-pro`
- ❌ `gemini-pro`
- ❌ `gemini-3-pro-preview` (preview not yet available)

## Usage Examples

### Command Line

```bash
# Use default OAuth path (~/.gemini/oauth_creds.json)
consult7 gemini-cli oauth:

# Specify custom OAuth path
consult7 gemini-cli oauth:~/my-custom-path/oauth_creds.json

# Test the connection
consult7 gemini-cli oauth: --test
```

### MCP Configuration (Claude Desktop)

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

### Python API

```python
from consult7.consultation import consultation_impl

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

## Features

- ✅ OAuth2 authentication (no API key needed)
- ✅ Auto token refresh
- ✅ Project ID discovery
- ✅ Free tier support
- ✅ Thinking/reasoning mode
- ✅ Streaming support

## Troubleshooting

### Authentication Error

```
Error: Failed to load Gemini CLI OAuth credentials
```

**Solution**: Run the `gemini` command again to re-authenticate

### Token Expired

The system will automatically refresh the token. If refresh fails, please re-authenticate:

```bash
gemini
```

### HTTP 403 Forbidden Error

```
Error: HTTP 403 - Access forbidden
```

**Possible causes:**
1. File is too large for context limit or contains content that Google blocks
2. OAuth token expired - run `gemini` to re-authenticate
3. Google account doesn't have access to Code Assist API

**Solutions:**
- Test with `consult7 gemini-cli oauth: --test` first (if it passes, OAuth is working)
- Re-authenticate: run `gemini` and log in again
- Try with smaller files or remove unnecessary content
- Verify that your Google account has access to Gemini Code Assist

### Project ID Not Found

The system will automatically create a new project ID via Google managed project (FREE tier).

**Note:** The FREE tier automatically gets assigned a managed project by Google. You don't need to specify a project ID manually.

## Cost

Gemini CLI uses Google's free tier - **completely free**
