# Phase 1: Data Model

**Feature**: Hybrid Consultation (Files + Database)  
**Date**: November 23, 2025

## Entity Definitions

### DatabaseConnection

Represents an active connection to a database system.

**Attributes**:
- `dsn: str` - Data Source Name (connection string)
- `database_type: DatabaseType` - Enum: MYSQL, POSTGRESQL, SQLITE, MONGODB
- `connection_pool: Queue[Connection]` - Pool of reusable connections
- `max_pool_size: int` - Maximum connections in pool (default: 5)
- `timeout: int` - Query timeout in seconds (default: 30)
- `is_readonly: bool` - Enforce read-only mode (always True)

**Validation Rules**:
- DSN must follow format: `protocol://[user[:password]@]host[:port]/[database]`
- Database type automatically detected from DSN scheme
- Timeout must be between 1 and 300 seconds
- Max pool size must be between 1 and 10

**State Transitions**:
```
[Created] → connect() → [Connected]
[Connected] → disconnect() → [Closed]
[Connected] → on_error → [Error] → reconnect() → [Connected]
```

---

### QueryRequest

Represents a single database query to be executed.

**Attributes**:
- `query_text: str` - SQL query or database-specific command
- `query_id: str` - Hash of query text (for logging, non-sensitive)
- `is_validated: bool` - Passed read-only validation
- `estimated_tokens: int` - Estimated token count for results

**Validation Rules**:
- Query text cannot be empty
- Must not contain write operations: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
- Maximum query length: 10,000 characters
- Must be valid SQL/command syntax for target database type

**Relationships**:
- Belongs to one `ConsultationRequest`
- Produces one `QueryResult`

---

### QueryResult

Represents the output from an executed database query.

**Attributes**:
- `query_id: str` - Reference to originating QueryRequest
- `rows: List[Dict[str, Any]]` - Query results as list of row dictionaries
- `row_count: int` - Number of rows returned
- `column_names: List[str]` - Column names in result set
- `execution_time_ms: int` - Query execution duration in milliseconds
- `is_truncated: bool` - Whether results were truncated for token budget
- `truncated_at_row: Optional[int]` - Row number where truncation occurred
- `error: Optional[str]` - Error message if query failed

**Validation Rules**:
- Row count must match len(rows) unless truncated
- Execution time must be non-negative
- If error is set, rows must be empty
- If is_truncated, truncated_at_row must be set

**State Diagram**:
```
[Pending] → execute() → [Success] with rows OR [Failed] with error
[Success] → truncate() → [Truncated] (if token budget exceeded)
```

---

### ConsultationRequest

Extended from existing entity to include database parameters.

**New Attributes** (in addition to existing):
- `database_queries: Optional[List[QueryRequest]]` - Database queries to execute
- `database_dsn: Optional[str]` - Database connection string
- `query_timeout: int` - Timeout for each query (default: 30s)
- `max_result_rows: int` - Maximum rows per query (default: 10,000)

**Validation Rules**:
- At least one of `files` or `database_queries` must be provided
- If `database_queries` provided, `database_dsn` is required
- If only `database_dsn` provided without queries, reject with error
- File patterns follow existing validation (absolute paths, wildcards in filenames only)

**Modes**:
1. **Files Only** (existing): `files` provided, no database params
2. **Database Only** (new): `database_queries` + `database_dsn`, no files
3. **Hybrid** (new): `files` + `database_queries` + `database_dsn`

---

### ContentBundle

Extended from existing entity to include database results.

**New Attributes** (in addition to existing):
- `database_results: List[QueryResult]` - Formatted database query results
- `database_token_count: int` - Tokens consumed by database results
- `total_token_count: int` - `file_token_count + database_token_count`
- `is_database_truncated: bool` - Whether database results were truncated

**Token Budget Calculation**:
```
available_tokens = model_context_length * 0.8  # Safety factor
output_reserve = available_tokens * 0.2
max_input_tokens = available_tokens - output_reserve

if (file_tokens + database_tokens) > max_input_tokens:
    # Truncate database results first
    max_db_tokens = max_input_tokens - file_tokens
    truncate_database_results_to_fit(max_db_tokens)
```

**Formatting**:
```
═══════════════════════════════════════
FILES TO PROCESS
═══════════════════════════════════════
[file content sections...]

═══════════════════════════════════════
DATABASE RESULTS
═══════════════════════════════════════
Query 1: SELECT * FROM users LIMIT 10;
───────────────────────────────────────
Row 1:
  id: 1
  name: Alice
  email: alice@example.com
...

Total content: 850KB from 12 files + 2 DB queries
Estimated tokens: ~175,000 (Model limit: 200,000)
```

---

### DatabaseAdapter (Abstract)

Base class for database-specific query handlers.

**Abstract Methods**:
- `connect(dsn: str) -> Connection` - Establish database connection
- `validate_query(query: str) -> bool` - Validate query is read-only
- `execute_query(query: str, timeout: int) -> QueryResult` - Execute and return results
- `format_result(result: QueryResult) -> str` - Format for AI consumption
- `close_connection(conn: Connection) -> None` - Clean up connection

**Concrete Implementations**:
- `MySQLAdapter`: MySQL/MariaDB specific handling
- `PostgreSQLAdapter`: PostgreSQL specific handling
- `SQLiteAdapter`: SQLite file-based database handling
- `MongoDBAdapter`: MongoDB document database handling

**Validation Strategies**:
```python
# SQL databases (MySQL, PostgreSQL, SQLite)
def validate_query(query: str) -> bool:
    # Regex check for write operations
    write_pattern = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b'
    if re.search(write_pattern, query, re.IGNORECASE):
        return False
    # Database-specific read-only mode enforcement
    self.set_readonly_mode()
    return True

# MongoDB
def validate_query(command: str) -> bool:
    # Only allow find, aggregate, count operations
    allowed_ops = ['find', 'findOne', 'aggregate', 'count', 'distinct']
    if not any(op in command for op in allowed_ops):
        return False
    return True
```

---

### ConnectionPool

Manages connection pooling per DSN.

**Attributes**:
- `dsn_hash: str` - Hash of DSN (non-sensitive identifier)
- `connections: Queue[Connection]` - Available connections
- `active_connections: Set[Connection]` - Currently in-use connections
- `max_size: int` - Maximum pool size (default: 5)
- `current_size: int` - Current number of connections
- `adapter: DatabaseAdapter` - Database-specific adapter

**Operations**:
```python
def acquire_connection() -> Connection:
    # Try to get from pool
    if not connections.empty():
        return connections.get()
    # Create new if under max_size
    if current_size < max_size:
        conn = adapter.connect(dsn)
        current_size += 1
        return conn
    # Wait for available connection (with timeout)
    return connections.get(timeout=30)

def release_connection(conn: Connection) -> None:
    # Return to pool if healthy
    if conn.is_healthy():
        connections.put(conn)
    else:
        conn.close()
        current_size -= 1
```

**Lifecycle**:
- Created on first query to a DSN
- Persists across multiple queries in same consultation
- Cleaned up after consultation completes
- Connections timeout after 5 minutes of inactivity

---

## Entity Relationships

```
ConsultationRequest
  ├── files: List[str] (existing)
  ├── database_queries: List[QueryRequest] (new)
  └── database_dsn: str (new)
       │
       ↓
ConnectionPool (per DSN)
  ├── adapter: DatabaseAdapter
  └── connections: Queue[Connection]
       │
       ↓
QueryRequest → execute() → QueryResult
       │
       ↓
ContentBundle
  ├── file_contents (existing)
  └── database_results: List[QueryResult] (new)
       │
       ↓
LLM Provider (existing, unchanged)
```

## Validation Rules Summary

1. **DSN Validation**: Must be valid URL format with required components
2. **Query Validation**: Must pass read-only checks (regex + database mode)
3. **Token Budget**: Files + database must fit within model context window
4. **Timeout Enforcement**: Queries must complete within configured timeout
5. **Result Set Limits**: Maximum rows per query enforced
6. **Connection Pooling**: Maximum connections per DSN enforced
7. **Error Handling**: All errors include actionable hints (Constitution Principle V)

## State Management

**Stateless Design** (Constitution Principle I):
- No persistent state between consultations
- Connection pools created per consultation
- All parameters passed explicitly
- Connection cleanup automatic on consultation completion

**Concurrent Handling**:
- Sequential processing per DSN (prevents race conditions)
- Shared file processing (avoid re-reading same files)
- Independent consultations don't interfere

## Next Steps

With data model defined, proceed to:
1. Define MCP tool contract (tool_definitions.py updates)
2. Create quickstart guide with usage examples
3. Update agent context files
