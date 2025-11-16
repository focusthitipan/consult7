# Qwen Code Provider Setup Guide

## Overview

Qwen Code provider ให้คุณใช้งาน Alibaba Qwen models ผ่าน OAuth authentication โดยไม่ต้องใช้ API key

## Prerequisites

1. มี Qwen account และ authenticate แล้ว
2. OAuth credentials ต้องอยู่ที่ `~/.qwen/oauth_creds.json`

## Authentication Setup

### วิธีที่ 1: ใช้ Qwen Code CLI (แนะนำ)

```bash
# ติดตั้ง Qwen Code CLI
npm install -g qwen-code-cli

# Authenticate
qwen-code auth login
```

### วิธีที่ 2: Manual Setup

สร้างไฟล์ `~/.qwen/oauth_creds.json` ด้วยโครงสร้างดังนี้:

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

### ผ่าน OAuth (2 models)

- `qwen3-coder-plus` - High-performance code analysis (context: 1M, max output: 65k)
- `qwen3-coder-flash` - Fast code analysis optimized for speed (context: 1M, max output: 65k)

### ⚠️ ข้อจำกัด OAuth

รองรับเฉพาะ **qwen3-coder-plus** และ **qwen3-coder-flash** ผ่าน OAuth

Models อื่นๆ **ไม่รองรับ OAuth** (ต้องใช้ API Key):
- ❌ `qwen3-max`
- ❌ `qwen-plus`
- ❌ `qwen-flash`
- ❌ `qwen3-vl-plus` (vision model)

## Usage Examples

### Command Line

```bash
# ใช้ default OAuth path (~/.qwen/oauth_creds.json)
consult7 qwen-code oauth:

# ระบุ custom OAuth path
consult7 qwen-code oauth:~/my-custom-path/oauth_creds.json

# ใช้ qwen3-coder-flash สำหรับความเร็ว
consult7 qwen-code oauth: --model qwen3-coder-flash

# ทดสอบการเชื่อมต่อ
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
### Python API

```python
from consult7.consultation import consultation_impl

# ใช้ qwen3-coder-plus (default)
result = await consultation_impl(
    files=["/path/to/file.py"],
    query="Review this code",
    model="qwen3-coder-plus",
    mode="fast",
    provider="qwen-code",
    api_key=None  # ใช้ default path: ~/.qwen/oauth_creds.json
)

# ใช้ qwen3-coder-flash สำหรับความเร็ว
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

- ✅ OAuth2 authentication (ไม่ต้องใช้ API key)
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

**Solution**: ตรวจสอบว่าไฟล์ `~/.qwen/oauth_creds.json` มีอยู่และมี format ถูกต้อง

### Token Expired

ระบบจะ auto-refresh token โดยอัตโนมัติ หาก refresh ไม่สำเร็จ:

1. ตรวจสอบ `refresh_token` ใน credentials file
2. Authenticate ใหม่ด้วย Qwen Code CLI

### 401 Unauthorized Error

หาก token หมดอายุและ refresh ไม่สำเร็จ ให้:

```bash
qwen-code auth logout
qwen-code auth login
```

## Performance Tips

- ใช้ `qwen3-coder-plus` สำหรับ high-performance code analysis
- ใช้ `qwen3-coder-flash` สำหรับ quick responses และ fast analysis
- Mode `fast` เหมาะสำหรับ quick queries
- Mode `mid` เพิ่ม reasoning สำหรับ complex analysis
- Mode `think` สำหรับ deep analysis (แนะนำกับ coder-plus)

**Note**: หากต้องการใช้ models อื่นๆ (qwen3-max, qwen-plus, etc.) ต้องใช้ API Key แทน OAuth

## Cost

Qwen Code OAuth มี free tier และ paid tiers - ตรวจสอบ quota ของคุณที่ Qwen dashboard
