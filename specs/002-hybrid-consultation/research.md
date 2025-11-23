# Phase 0: Research & Technology Decisions

**Feature**: Hybrid Consultation (Files + Database)  
**Date**: November 23, 2025  
**Status**: Research Complete

## Research Questions

### 1. Database Driver Selection

**Question**: Which Python database drivers should we use for multi-database support?

**Research Findings**:

| Database | Driver | Rationale |
|----------|--------|-----------|
| **MySQL** | `pymysql` | Pure Python, no external dependencies, async-compatible via asyncio |
| **PostgreSQL** | `psycopg2` | Industry standard, mature, well-documented, excellent error messages |
| **SQLite** | `sqlite3` (stdlib) | Built-in Python library, zero dependencies, perfect for file-based DBs |
| **MongoDB** | `pymongo` | Official MongoDB driver, comprehensive query support, cursor handling |

**Alternatives Considered**:
- SQLAlchemy: Too heavy for read-only queries, adds unnecessary abstraction layer
- asyncpg (PostgreSQL): Async-only, complicates sync/async boundary
- mysql-connector-python: Official but slower than pymysql

**Decision**: Use native drivers listed above
- **Rationale**: Minimal dependencies, direct control over connection/query handling, easier debugging

### 2. Connection Pooling Strategy

**Question**: How to implement connection pooling for concurrent consultations?

**Research Findings**:

**Option A**: Per-DSN connection pool using `queue.Queue`
```python
# Lightweight, Python stdlib only
connection_pools: Dict[str, Queue[Connection]] = {}
```

**Option B**: Library-based pooling (DBUtils, SQLAlchemy pooling)
- Adds dependencies
- Over-engineered for read-only use case

**Option C**: No pooling (create fresh connection per query)
- Simple but slow
- Expensive for multiple queries in single consultation

**Decision**: Implement Option A - Per-DSN connection pool using stdlib `queue.Queue`
- **Rationale**: 
  - Lightweight, no extra dependencies
  - Sufficient for sequential-per-DSN concurrency model
  - Easy to implement max pool size (e.g., 5 connections per DSN)
  - Automatic cleanup on consultation completion

### 3. Query Validation Approach

**Question**: How to validate and block write operations before execution?

**Research Findings**:

**Option A**: SQL parsing library (sqlparse)
```python
import sqlparse
tokens = sqlparse.parse(query)[0].tokens
# Parse and analyze AST
```
- Pros: Accurate, handles complex SQL
- Cons: New dependency, performance overhead

**Option B**: Regex-based keyword detection
```python
WRITE_OPS = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b'
if re.search(WRITE_OPS, query, re.IGNORECASE):
    raise ValidationError()
```
- Pros: Fast, zero dependencies
- Cons: Can be bypassed with comments, string literals

**Option C**: Database-specific read-only modes
```python
# PostgreSQL
conn.set_session(readonly=True)
# MySQL
conn.cursor().execute("SET SESSION TRANSACTION READ ONLY")
```
- Pros: Database enforced, no parsing needed
- Cons: Database-specific implementation, not all DBs support

**Decision**: Hybrid approach - Regex validation + database read-only mode where supported
- **Rationale**:
  - Regex catches obvious violations fast (fail-fast)
  - Database read-only mode as secondary enforcement
  - Defense in depth

### 4. Result Set Formatting

**Question**: How to format database results for AI consumption?

**Research Findings**:

**Option A**: Markdown tables
```markdown
| id | name | email |
|----|------|-------|
| 1  | Alice | alice@example.com |
```
- Pros: Human-readable, compact
- Cons: Hard to format large columns, escaping issues

**Option B**: JSON format
```json
[
  {"id": 1, "name": "Alice", "email": "alice@example.com"}
]
```
- Pros: Structured, easy to parse, handles complex types
- Cons: Verbose for large result sets

**Option C**: Plain text with separators
```text
Query: SELECT * FROM users LIMIT 10;
───────────────────────────────────────
Row 1:
  id: 1
  name: Alice
  email: alice@example.com
Row 2:
  ...
```
- Pros: Most readable for AI, clear structure
- Cons: Most verbose

**Decision**: Option C - Plain text with separators for readability
- **Rationale**:
  - AI models perform better with clear text formatting
  - Matches existing file content formatting style in consult7
  - Easy to truncate rows when hitting token limits
  - No escaping issues

### 5. Token Budget Integration

**Question**: How to calculate combined file + database token usage?

**Research Findings**:

Current token estimation in `token_utils.py`:
```python
def estimate_tokens(text: str, model: str) -> int:
    # ~4 chars per token (English text average)
    return len(text) // 4
```

**Integration approach**:
```python
# 1. Calculate file content tokens (existing)
file_tokens = sum(estimate_tokens(content, model) for content in files)

# 2. Calculate database result tokens
db_result_text = format_database_results(query_results)
db_tokens = estimate_tokens(db_result_text, model)

# 3. Total input tokens
total_input_tokens = file_tokens + db_tokens

# 4. Check against budget
available_tokens = context_length * safety_factor
output_reserve = available_tokens * 0.2
max_input_tokens = available_tokens - output_reserve

if total_input_tokens > max_input_tokens:
    # Truncate database results first
    truncate_ratio = (max_input_tokens - file_tokens) / db_tokens
    truncate_database_results(query_results, truncate_ratio)
```

**Decision**: Extend existing token estimation with database result counting
- **Rationale**:
  - Reuses proven estimation logic
  - Files get priority (specified by user)
  - Database results truncated first (can re-run with LIMIT)
  - Maintains dynamic budget calculation (Principle III)

### 6. Error Handling & Observability

**Question**: What structured logging format should we use?

**Research Findings**:

**Option A**: Python logging module with JSON formatter
```python
import logging
import json

logger = logging.getLogger("consult7.database")
logger.info(json.dumps({
    "event": "query_executed",
    "dsn_hash": hash(dsn),
    "duration_ms": duration,
    "rows_returned": count
}))
```

**Option B**: Structured log strings
```python
logger.info(
    "query_executed dsn_hash=%s duration_ms=%d rows=%d",
    dsn_hash, duration, count
)
```

**Decision**: Option B - Structured log strings with standard Python logging
- **Rationale**:
  - Simpler, no JSON serialization overhead
  - Easy to grep and parse
  - Compatible with existing consult7 logging
  - Can upgrade to JSON later if needed

**Log Events**:
- `database_connection_opened`: DSN hash, database type
- `database_query_executed`: Query hash, duration, rows returned, truncated (yes/no)
- `database_connection_closed`: DSN hash, lifetime
- `database_error`: Error type, error message (sanitized), query hash
- `token_budget_exceeded`: File tokens, DB tokens, budget limit, truncation applied

### 7. DSN Parsing & Validation

**Question**: How to parse and validate database connection strings?

**Research Findings**:

**Option A**: urllib.parse
```python
from urllib.parse import urlparse

parsed = urlparse(dsn)
scheme = parsed.scheme  # mysql, postgresql, etc.
username = parsed.username
password = parsed.password
hostname = parsed.hostname
port = parsed.port
database = parsed.path.lstrip('/')
```
- Pros: Stdlib, handles URL encoding
- Cons: Manual validation needed

**Option B**: Dedicated DSN parsing library (dsnparse)
- Pros: Specialized for DSNs
- Cons: New dependency

**Decision**: Option A - urllib.parse with custom validation
- **Rationale**:
  - Zero dependencies
  - Simple validation logic
  - Consistent with Python ecosystem practices

**Validation Rules**:
- Scheme must be in: `mysql`, `postgresql`, `sqlite`, `mongodb`
- Username optional (SQLite doesn't need)
- Hostname required (except SQLite)
- Port defaults: MySQL/MariaDB(3306), PostgreSQL(5432), MongoDB(27017)
- Database name required

## Technology Stack Summary

### Dependencies to Add
```
pymysql==1.1.0
psycopg2-binary==2.9.9
pymongo==4.6.1
# sqlite3 is stdlib, no install needed
```

### No New Dependencies Required For
- Connection pooling: Use stdlib `queue.Queue`
- DSN parsing: Use stdlib `urllib.parse`
- Query validation: Use stdlib `re`
- Logging: Use stdlib `logging`

### Module Structure
```python
src/consult7/database/
├── __init__.py
├── connection.py      # Connection pooling, DSN parsing
├── adapters/
│   ├── __init__.py
│   ├── base.py        # BaseAdapter abstract class
│   ├── mysql.py       # MySQLAdapter
│   ├── postgresql.py  # PostgreSQLAdapter
│   ├── sqlite.py      # SQLiteAdapter
│   └── mongodb.py     # MongoDBAdapter
├── validation.py      # Query validation (read-only enforcement)
└── formatting.py      # Result formatting for AI
```

## Open Questions Resolved

All research questions have been answered with concrete decisions. No "NEEDS CLARIFICATION" items remain.

## Next Steps

Proceed to **Phase 1: Design & Contracts**
- Create data-model.md with entity definitions
- Define MCP tool schema extensions (consultation tool parameters)
- Write quickstart.md with usage examples
