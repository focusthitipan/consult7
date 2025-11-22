# MCP Tool Contract: consultation (Extended)

**Version**: 2.0 (adds database support)  
**Status**: Draft  
**Backward Compatible**: Yes (all new parameters optional)

## Tool Definition

### Name
`consultation`

### Description
Analyze files and/or database content using AI. Supports three modes:
1. **Files only**: Existing behavior (backward compatible)
2. **Database only**: New - analyze database schema/data
3. **Hybrid**: New - analyze files and database together

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "files": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Absolute file paths or patterns (*.py in filename only). Optional if db_queries provided."
    },
    "query": {
      "type": "string",
      "description": "Question or analysis request for AI",
      "required": true
    },
    "model": {
      "type": "string",
      "description": "Model name (e.g., gpt-4, claude-sonnet-4)",
      "required": true
    },
    "mode": {
      "type": "string",
      "enum": ["fast", "mid", "think"],
      "description": "Performance mode: fast (no reasoning), mid (moderate), think (deep reasoning)",
      "required": true
    },
    "output_file": {
      "type": "string",
      "description": "Optional: Save response to file (absolute path)"
    },
    "provider": {
      "type": "string",
      "description": "Optional: LLM provider override (openrouter, gemini-cli, qwen-code, github-copilot)"
    },
    "api_key": {
      "type": "string",
      "description": "Optional: API key or OAuth path override"
    },
    "db_queries": {
      "type": "array",
      "items": {"type": "string"},
      "description": "NEW: Database queries to execute (read-only). Optional if files provided."
    },
    "db_dsn": {
      "type": "string",
      "description": "NEW: Database DSN (Data Source Name). Required if db_queries provided. Format: protocol://[user[:password]@]host[:port]/[database]"
    },
    "db_timeout": {
      "type": "integer",
      "description": "NEW: Query timeout in seconds. Default: 30. Range: 1-300.",
      "default": 30
    },
    "db_max_rows": {
      "type": "integer",
      "description": "NEW: Maximum rows per query. Default: 10000. Range: 1-100000.",
      "default": 10000
    }
  },
  "required": ["query", "model", "mode"]
}
```

### Validation Rules

1. **Mode Combinations**:
   - Files only: `files` provided, no `db_queries` or `db_dsn`
   - Database only: `db_queries` + `db_dsn` provided, no `files`
   - Hybrid: `files` + `db_queries` + `db_dsn` all provided
   - Invalid: Neither `files` nor `db_queries` provided

2. **Database Parameters**:
   - If `db_queries` provided, `db_dsn` is REQUIRED
   - If `db_dsn` provided without `db_queries`, REJECT with error
   - `db_timeout` must be 1-300 seconds
   - `db_max_rows` must be 1-100,000

3. **File Patterns** (existing):
   - Must be absolute paths
   - Wildcards only in filename component
   - Auto-ignore: `__pycache__`, `.env`, `secrets.py`, `.DS_Store`, `.git`, `node_modules`

4. **Query Validation**:
   - Queries must be read-only operations
   - Blocked operations: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE
   - MongoDB: Only find, findOne, aggregate, count, distinct allowed

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {"type": "string", "enum": ["text"]},
          "text": {"type": "string"}
        }
      },
      "description": "AI analysis response"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "files_processed": {"type": "integer"},
        "queries_executed": {"type": "integer"},
        "total_tokens": {"type": "integer"},
        "file_tokens": {"type": "integer"},
        "database_tokens": {"type": "integer"},
        "is_truncated": {"type": "boolean"},
        "warnings": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    }
  }
}
```

## Usage Examples

### Example 1: Files Only (Existing Behavior)
```json
{
  "files": ["/Users/alice/project/src/**/*.py"],
  "query": "Find potential security vulnerabilities",
  "model": "gpt-4",
  "mode": "think"
}
```

**Expected Response**:
```json
{
  "content": [{
    "type": "text",
    "text": "Analysis of Python files...\n\n1. SQL Injection risk in users.py line 45..."
  }],
  "metadata": {
    "files_processed": 24,
    "queries_executed": 0,
    "total_tokens": 15000,
    "file_tokens": 15000,
    "database_tokens": 0,
    "is_truncated": false,
    "warnings": []
  }
}
```

### Example 2: Database Only
```json
{
  "db_queries": [
    "SHOW TABLES;",
    "DESCRIBE users;",
    "SELECT COUNT(*) FROM users;"
  ],
  "db_dsn": "mysql://root@localhost:3306/myapp",
  "query": "Analyze database schema structure",
  "model": "claude-sonnet-4",
  "mode": "mid"
}
```

**Expected Response**:
```json
{
  "content": [{
    "type": "text",
    "text": "Database Schema Analysis:\n\nTables: users, orders, products\n\nusers table:\n- id (INT PRIMARY KEY)\n- name (VARCHAR(255))\n- Missing indexes on email column..."
  }],
  "metadata": {
    "files_processed": 0,
    "queries_executed": 3,
    "total_tokens": 5000,
    "file_tokens": 0,
    "database_tokens": 5000,
    "is_truncated": false,
    "warnings": []
  }
}
```

### Example 3: Hybrid (Files + Database)
```json
{
  "files": ["/Users/alice/project/src/models/user.py"],
  "db_queries": [
    "DESCRIBE users;",
    "SELECT * FROM users LIMIT 5;"
  ],
  "db_dsn": "mysql://root@localhost:3306/myapp",
  "query": "Are there any inconsistencies between the User model and database schema?",
  "model": "gpt-4",
  "mode": "think",
  "db_timeout": 30,
  "db_max_rows": 1000
}
```

**Expected Response**:
```json
{
  "content": [{
    "type": "text",
    "text": "Schema Inconsistency Analysis:\n\n1. Missing Field: The User model defines 'phone_number' but this column doesn't exist in the database...\n2. Type Mismatch: Model defines 'age' as Integer but database has SMALLINT...\n3. Unused Column: Database has 'legacy_id' column not referenced in model..."
  }],
  "metadata": {
    "files_processed": 1,
    "queries_executed": 2,
    "total_tokens": 8500,
    "file_tokens": 3000,
    "database_tokens": 5500,
    "is_truncated": false,
    "warnings": []
  }
}
```

### Example 4: Token Budget Exceeded (Truncation)
```json
{
  "files": ["/Users/alice/project/src/**/*.ts"],
  "db_queries": ["SELECT * FROM large_table LIMIT 50000;"],
  "db_dsn": "postgresql://user@localhost:5432/bigdb",
  "query": "Analyze code and data patterns",
  "model": "gpt-4",
  "mode": "mid"
}
```

**Expected Response with Warning**:
```json
{
  "content": [{
    "type": "text",
    "text": "Analysis based on 50 TypeScript files and 10,000 rows from large_table (truncated)..."
  }],
  "metadata": {
    "files_processed": 50,
    "queries_executed": 1,
    "total_tokens": 120000,
    "file_tokens": 80000,
    "database_tokens": 40000,
    "is_truncated": true,
    "warnings": [
      "Database results truncated: 50000 rows requested, 10000 rows included to fit token budget",
      "Recommendation: Reduce file count or add WHERE clause to limit database results"
    ]
  }
}
```

## Error Responses

### Error 1: Invalid Mode Combination
```json
{
  "error": {
    "code": "INVALID_PARAMETERS",
    "message": "Must provide either 'files' or 'db_queries', or both.\n  Hint: Add file patterns (e.g., ['/path/to/src/**/*.py']) or database queries"
  }
}
```

### Error 2: Missing DSN
```json
{
  "error": {
    "code": "MISSING_REQUIRED_PARAMETER",
    "message": "Parameter 'db_dsn' is required when 'db_queries' is provided.\n  Hint: Add database connection string, e.g., 'mysql://user@host:3306/database'"
  }
}
```

### Error 3: Write Operation Blocked
```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "Query validation failed: Write operation 'INSERT' not permitted.\n  Hint: Only read operations allowed (SELECT, SHOW, DESCRIBE, PRAGMA, find, aggregate)"
  }
}
```

### Error 4: Connection Failed
```json
{
  "error": {
    "code": "DATABASE_CONNECTION_ERROR",
    "message": "Failed to connect to database: Authentication failed for user 'root'.\n  Hint: Verify DSN credentials and database accessibility. Test connection: mysql -h localhost -u root -p myapp"
  }
}
```

### Error 5: Query Timeout
```json
{
  "error": {
    "code": "QUERY_TIMEOUT",
    "message": "Query exceeded 30 second timeout limit.\n  Hint: Optimize query with WHERE clause or indexes, or increase timeout: 'db_timeout': 60"
  }
}
```

## Backward Compatibility

All database-related parameters are **optional**. Existing usage patterns continue to work unchanged:

**Before** (v1.0):
```json
{
  "files": ["/path/**/*.py"],
  "query": "Analyze code",
  "model": "gpt-4",
  "mode": "fast"
}
```

**After** (v2.0): Works identically, no changes required

## Implementation Notes

1. **Parameter Processing Order**:
   - Validate mode combination (files/db/hybrid)
   - Parse DSN if provided
   - Validate queries (read-only check)
   - Discover files (existing logic)
   - Execute database queries
   - Calculate token budget
   - Truncate database results if needed
   - Format combined content
   - Call LLM provider

2. **Connection Management**:
   - Create connection pool per DSN
   - Reuse connections across queries
   - Close all connections on completion

3. **Error Priority**:
   - Parameter validation errors → fail fast (before any I/O)
   - Connection errors → include DSN troubleshooting
   - Query errors → include query syntax hints
   - Token budget errors → include reduction suggestions

4. **Logging** (structured, non-sensitive):
   - `database_connection_opened`: DSN hash, database type
   - `database_query_executed`: Query hash, duration, rows, truncated
   - `database_connection_closed`: DSN hash, lifetime
   - `token_budget_calculation`: File tokens, DB tokens, budget, truncated
