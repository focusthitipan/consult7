# GitHub Copilot Provider Setup

## Overview

The GitHub Copilot provider enables Consult7 to use GitHub Copilot's AI models (GPT-4o, Claude, Gemini, Grok) through **OAuth Device Flow** authentication.

### Key Features
- ✅ **No API key required** - uses OAuth Device Flow
- ✅ **No VS Code required** - authenticates directly with GitHub API
- ✅ **Secure token storage** - AES-256-GCM encryption
- ✅ **Multiple models** - GPT-4o, GPT-5, Claude, Gemini, Grok

## Prerequisites

1. **Active GitHub Copilot Subscription** ⚠️ **REQUIRED**
   - Individual subscription ($10/month)
   - Business subscription (via organization)
   - Free trial (if available)
   - Check at: https://github.com/settings/copilot

2. **Python 3.11+** with pip installed

3. **Web Browser** for one-time authentication

## Installation

### 1. Install Consult7

```powershell
# Clone repository (if not already done)
git clone https://github.com/focusthitipan/consult7.git
cd consult7

# Install in editable mode
pip install -e .
```

### 2. Verify Installation

```powershell
consult7 --help
```

You should see `github-copilot` in the provider list.

## Authentication (No VS Code Required!)

GitHub Copilot uses **OAuth Device Flow** - authenticate directly with GitHub through your browser. VS Code is **NOT** required.

### First-Time Setup

#### Option 1: Interactive Test (Recommended)

```powershell
# Run test - will prompt for authentication if needed
consult7 github-copilot oauth: --test
```

**Interactive Flow:**

1. **System checks for token:**
   ```
   OAuth Token: Not found
   
   [WARNING] No GitHub Copilot token found!
             You need to authenticate first.
   
   Would you like to authenticate now? (yes/no):
   ```

2. **Type `yes` to authenticate**

3. **OAuth Device Flow starts:**
   ```
   Please visit: https://github.com/login/device
   Enter code: ABCD-1234
   
   Code expires in 15 minutes
   Waiting for authorization...
   ```

4. **Browser opens automatically** (or copy URL manually)

5. **On GitHub page:**
   - Login to GitHub (if not already logged in)
   - Enter the displayed device code (`ABCD-1234`)
   - Click "Continue"
   - Authorize "GitHub Copilot API" access

6. **Back to console:**
   ```
   [SUCCESS] Authentication successful!
   Token scope: ...
   
   [SUCCESS] Authentication successful! Continuing with test...
   
   Testing github-copilot API connection...
   OAuth Token: ~/.consult7/github-copilot_oauth_token.enc (encrypted)
   Test Model: gpt-4o
   Test Mode: fast
   
   Running test query...
   
   [PASSED] Test PASSED
   Response preview: ...
   ```

7. **Token saved:**
   - Location: `%USERPROFILE%\.consult7\github-copilot_oauth_token.enc`
   - Encrypted with AES-256-GCM
   - Valid until expiry or revoked

#### Option 2: Authenticate Without Test

```powershell
# Just authenticate (no test)
consult7 github-copilot oauth:
```

This will run OAuth flow and exit after saving the token.

### Subsequent Usage

Once authenticated, just use `oauth:` - the stored token is loaded automatically:

```powershell
consult7 github-copilot oauth: --test
```

### Custom Token Path

Store token in a custom location:

```powershell
# First time with custom path
consult7 github-copilot oauth:/custom/path/token.json --test

# Use custom path later
consult7 github-copilot oauth:/custom/path/token.json --test
```

## Available Models

> **Note**: GitHub Copilot limits context/output for IDE usage. Values shown reflect actual limits, not model capabilities.

### GPT-4 Models (Standard Chat)
| Model | Context | Max Output | Best For |
|-------|---------|-----------|----------|
| `gpt-4o` | 128K | 16K | General-purpose, balanced |
| `gpt-4.1` | 128K | 16K | Improved reasoning |

### GPT-5 Models
| Model | Context | Max Output | Best For |
|-------|---------|-----------|----------|
| `gpt-5` | 128K | 16K | Latest flagship (Base) |
| `gpt-5-mini` | 128K | **64K** | Fast + high output |
| `gpt-5.1` | 128K | 16K | Cutting edge (Latest) |

### Claude Models (IDE-optimized limits)
| Model | Context | Max Output | Best For |
|-------|---------|-----------|----------|
| `claude-haiku-4.5` | 128K* | 16K* | Fast and economical |
| `claude-sonnet-4` | 128K* | 16K* | Balanced performance |
| `claude-sonnet-4.5` | 128K* | 16K* | Best quality |

*Context reduced from 200K, Output increased from 8K for IDE usage

### Gemini Models (Reduced for agent competition)
| Model | Context | Max Output | Best For |
|-------|---------|-----------|----------|
| `gemini-2.5-pro` | 128K* | **64K*** | High output tasks |
| `gemini-3-pro-preview` | 128K* | **64K*** | Experimental (Preview) |

*Context massively reduced from 1M, Output increased to 64K

### X AI Models (High context window)
| Model | Context | Max Output | Best For |
|-------|---------|-----------|----------|
| `grok-code-fast-1` | 128K | 10K | Fast responses, high output focus |

## Claude Desktop Configuration

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "consult7-github-copilot": {
      "command": "consult7",
      "args": ["github-copilot", "oauth:"],
      "env": {}
    }
  }
}
```

**Important**: Must authenticate via command line BEFORE using with Claude Desktop:
```powershell
consult7 github-copilot oauth: --test
```

## Usage Examples

### Via Claude Desktop

Once configured, use the `mcp_consult7-gith_consultation` tool in Claude Desktop:

```
Analyze these Python files for security vulnerabilities:
[Use consultation tool]
Files: ["h:/project/src/*.py", "h:/project/tests/*.py"]
Query: "Find security vulnerabilities and suggest fixes"
Model: "gpt-4o"
Mode: "think"
```

### Via Command Line

```powershell
# Test connection
consult7 github-copilot oauth: --test

# Start MCP server (for Claude Desktop)
consult7 github-copilot oauth:
```

## Reasoning Modes

GitHub Copilot supports 3 reasoning modes:

- **fast**: No reasoning, fastest response (default for most models)
- **mid**: Moderate reasoning (50% thinking budget)
- **think**: Maximum reasoning (full thinking budget, best for o1 models)

### Models with Reasoning Support

- `o1-preview`: 32K thinking tokens
- `o1-mini`: 65K thinking tokens

Other models (gpt-4o, claude, gemini) run in fast mode only.

## Troubleshooting

### Authentication Fails

**Problem**: "OAuth authentication failed"

**Solutions**:
1. **Check Copilot subscription**: https://github.com/settings/copilot
   - Must show "Active subscription" status
   - Individual or Business plan required
2. **Delete old token**: 
   ```powershell
   Remove-Item "$env:USERPROFILE\.consult7\github-copilot_oauth_token.enc" -Force
   ```
3. **Re-authenticate**: 
   ```powershell
   consult7 github-copilot oauth: --test
   ```
4. **Check firewall**: Ensure GitHub API access not blocked

### Token Expired

**Problem**: "Access token expired"

**Solution**: Re-authenticate (token exchange happens automatically)
```powershell
consult7 github-copilot oauth: --test
```

### Model Not Available

**Problem**: "Model gpt-4o not available"

**Solutions**:
1. Check your subscription tier (some models require Business subscription)
2. Try alternative model: `gpt-4o-mini`, `claude-3.5-sonnet`

### Claude Desktop Can't Connect

**Problem**: MCP server not responding

**Solutions**:
1. Verify command-line authentication works:
   ```powershell
   consult7 github-copilot oauth: --test
   ```
2. Check config path: `%APPDATA%\Claude\claude_desktop_config.json`
3. Restart Claude Desktop after config changes
4. Check Claude logs: `%APPDATA%\Claude\logs\`

### Rate Limits

**Problem**: "Rate limit exceeded"

**Behavior**: Fails immediately (no retry)

**Solution**: Wait for rate limit reset (shown in error message)

## Security Notes

1. **Token Encryption**: OAuth tokens stored with AES-256-GCM encryption
2. **Token Location**: `%USERPROFILE%\.consult7\github-copilot_oauth_token.enc`
3. **Token Expiry**: Tokens expire after period of inactivity
4. **Permissions**: Token grants access to GitHub Copilot API only
5. **No VS Code Data**: Does not access VS Code settings or extensions
6. **Revocation**: Revoke at https://github.com/settings/applications

## FAQ

### Q: Do I need VS Code installed?
**A: No!** This provider uses OAuth Device Flow to authenticate directly with GitHub API. VS Code is not required.

### Q: Can I use this without VS Code Copilot extension?
**A: Yes!** As long as you have an active GitHub Copilot subscription, you can authenticate and use models through this provider.

### Q: What's the difference from VS Code Copilot?
**A:** 
- **VS Code Copilot**: Code completion in editor
- **Consult7 GitHub Copilot**: File analysis with large context windows (up to 1M tokens)

### Q: Does this consume my GitHub Copilot quota?
**A: Yes.** Uses the same GitHub Copilot subscription as VS Code extension.

### Q: Can I use this on a server without GUI?
**A: Partially.** Initial authentication requires a browser, but you can:
1. Authenticate on local machine
2. Copy token file to server: `%USERPROFILE%\.consult7\github-copilot_oauth_token.enc`

## Advanced Configuration

### Environment Variables

None required - all configuration via command-line arguments.

### Multiple Token Profiles

Use custom paths for different profiles:

```powershell
# Work profile
consult7 github-copilot oauth:/.github/work_token.json --test

# Personal profile
consult7 github-copilot oauth:/.github/personal_token.json --test
```

### Integration with CI/CD

Not recommended - GitHub Copilot OAuth designed for interactive use. For automation, consider OpenRouter provider instead.

## Next Steps

- [Main README](../README.md) - Overview and all providers
- [Qwen Code Setup](./QWEN_CODE_SETUP.md) - Alternative free provider
- [Gemini CLI Setup](./GEMINI_CLI_SETUP.md) - Alternative free provider

## Support

- Issues: https://github.com/focusthitipan/consult7/issues
- Discussions: https://github.com/focusthitipan/consult7/discussions
