# Gemini CLI Provider Setup Guide

## Overview

Gemini CLI provider ให้คุณใช้งาน Google Gemini models ผ่าน OAuth authentication โดยไม่ต้องใช้ API key

## Prerequisites

1. ติดตั้ง Gemini CLI tool:
   ```bash
   npm install -g @google/generative-ai-cli
   ```

2. Authenticate ด้วย Google account:
   ```bash
   gemini
   ```
   - ระบบจะเปิดบราวเซอร์ให้คุณ login ด้วย Google
   - Credentials จะถูกบันทึกที่ `~/.gemini/oauth_creds.json`

## Supported Models

- `gemini-2.5-flash` - Fast responses (context: 1.048M, max output: 64k, free tier)
- `gemini-2.5-pro` - High quality analysis (context: 1.048M, max output: 64k, free tier)

### ⚠️ ข้อจำกัด OAuth

รองรับเฉพาะ **Gemini 2.5 Series** เท่านั้น:
- ✅ `gemini-2.5-flash`
- ✅ `gemini-2.5-pro`

Models ที่ **ไม่รองรับ** (HTTP 404):
- ❌ `gemini-1.5-pro`
- ❌ `gemini-1.5-flash`
- ❌ `gemini-1.0-pro`
- ❌ `gemini-pro`

## Usage Examples

### Command Line

```bash
# ใช้ default OAuth path (~/.gemini/oauth_creds.json)
consult7 gemini-cli oauth:

# ระบุ custom OAuth path
consult7 gemini-cli oauth:~/my-custom-path/oauth_creds.json

# ทดสอบการเชื่อมต่อ
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
    api_key=None  # ใช้ default path: ~/.gemini/oauth_creds.json
    # หรือ api_key="/custom/path/oauth_creds.json" สำหรับ custom path
)
```

## Features

- ✅ OAuth2 authentication (ไม่ต้องใช้ API key)
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

**Solution**: รัน `gemini` command ใหม่เพื่อ authenticate

### Token Expired

ระบบจะ auto-refresh token โดยอัตโนมัติ หาก refresh ไม่สำเร็จให้ authenticate ใหม่

### HTTP 403 Forbidden Error

```
Error: HTTP 403 - Access forbidden
```

**สาเหตุที่เป็นไปได้:**
1. ไฟล์ใหญ่เกิน context limit หรือมีเนื้อหาที่ Google ห้าม
2. OAuth token หมดอายุ - ให้รัน `gemini` เพื่อ re-authenticate
3. Google account ไม่มีสิทธิ์เข้าถึง Code Assist API

**Solution:**
- ทดสอบด้วย `consult7 gemini-cli oauth: --test` ก่อน (ถ้าผ่านแสดงว่า OAuth ใช้งานได้)
- Re-authenticate: `gemini` แล้ว login ใหม่
- ลองใช้ไฟล์ที่เล็กกว่า หรือตัดเนื้อหาที่ไม่จำเป็นออก
- ตรวจสอบว่า Google account มี access เข้า Gemini Code Assist

### Project ID Not Found

ระบบจะสร้าง project ID ใหม่โดยอัตโนมัติผ่าน Google managed project (FREE tier)

**หมายเหตุ:** FREE tier จะถูก auto-assign managed project จาก Google โดยอัตโนมัติ ไม่ต้องระบุ project ID เอง

## Cost

Gemini CLI ใช้ free tier ของ Google - **ไม่มีค่าใช้จ่าย**
