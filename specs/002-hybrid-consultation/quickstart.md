# Quickstart: Hybrid Consultation

**Feature**: Files + Database Analysis  
**Version**: 2.0  
**Date**: November 23, 2025

## Installation

### Prerequisites
- Python 3.11 or higher
- consult7 MCP server installed
- Database access credentials

### Install Database Drivers

```bash
pip install pymysql psycopg2-binary pymongo
# sqlite3 is included in Python stdlib
```

## Configuration

### 1. Set Environment Variable for DSN

```bash
# Windows PowerShell
$env:DB_DSN = "mysql://user:password@localhost:3306/myapp"

# macOS/Linux
export DB_DSN="mysql://user:password@localhost:3306/myapp"
```

### 2. DSN Format by Database Type

```
MySQL:      mysql://user:password@host:3306/database
PostgreSQL: postgresql://user:password@host:5432/database
SQLite:     sqlite:///./path/to/database.db
MongoDB:    mongodb://user:password@host:27017/database
```

**Security Note**: Use environment variables. Never hardcode credentials in files.

## Usage Patterns

### Pattern 1: Files Only (Existing)

**Use Case**: Analyze code without database context

```bash
# Via MCP client (VS Code, Claude Desktop, etc.)
Tool: consultation
Parameters:
{
  "files": ["/Users/alice/project/src/**/*.py"],
  "query": "Find security vulnerabilities",
  "model": "gpt-4",
  "mode": "think"
}
```

**Output**: Code analysis without database information

---

### Pattern 2: Database Only

**Use Case**: Analyze database schema or data without code

```bash
Tool: consultation
Parameters:
{
  "db_queries": [
    "SHOW TABLES;",
    "DESCRIBE users;",
    "DESCRIBE orders;",
    "SELECT COUNT(*) FROM users;",
    "SELECT COUNT(*) FROM orders;"
  ],
  "db_dsn": "${DB_DSN}",
  "query": "Analyze database schema and suggest optimizations",
  "model": "claude-sonnet-4",
  "mode": "mid"
}
```

**Output**: Schema analysis, index recommendations, normalization suggestions

---

### Pattern 3: Hybrid (Files + Database)

**Use Case**: Verify code matches database schema

```bash
Tool: consultation
Parameters:
{
  "files": ["/Users/alice/project/src/models/**/*.ts"],
  "db_queries": [
    "SHOW TABLES;",
    "DESCRIBE users;",
    "DESCRIBE orders;",
    "DESCRIBE products;"
  ],
  "db_dsn": "${DB_DSN}",
  "query": "Are there any inconsistencies between TypeScript models and database schema?",
  "model": "gpt-4",
  "mode": "think"
}
```

**Output**: 
- Fields in code but missing in database
- Database columns not used in code
- Type mismatches
- Validation discrepancies

---

### Pattern 4: Data Quality Analysis

**Use Case**: Check data patterns against code logic

```bash
Tool: consultation
Parameters:
{
  "files": ["/Users/alice/project/src/services/order-validator.py"],
  "db_queries": [
    "SELECT status, COUNT(*) FROM orders GROUP BY status;",
    "SELECT * FROM orders WHERE status = 'pending' LIMIT 100;",
    "SELECT MIN(created_at), MAX(created_at) FROM orders;"
  ],
  "db_dsn": "${DB_DSN}",
  "query": "Does the order validation logic handle all status values found in the database?",
  "model": "gpt-4",
  "mode": "mid",
  "db_max_rows": 1000
}
```

**Output**: Edge cases, missing validations, data anomalies

---

### Pattern 5: API Endpoint Verification

**Use Case**: Check if API implementation matches database design

```bash
Tool: consultation
Parameters:
{
  "files": ["/Users/alice/project/src/routes/**/*.go"],
  "db_queries": [
    "SHOW CREATE TABLE users;",
    "SHOW INDEXES FROM users;",
    "EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';"
  ],
  "db_dsn": "${DB_DSN}",
  "query": "Review API endpoint implementations for potential N+1 query problems and missing indexes",
  "model": "claude-sonnet-4",
  "mode": "think",
  "db_timeout": 60
}
```

**Output**: N+1 issues, missing indexes, query optimization suggestions

---

## Common Scenarios

### Scenario 1: Schema Migration Planning

**Goal**: Assess impact of database changes on codebase

```bash
{
  "files": ["/path/to/src/**/*.rb"],
  "db_queries": [
    "DESCRIBE users;",
    "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name IN ('users', 'profiles');"
  ],
  "db_dsn": "postgresql://user@localhost:5432/prod",
  "query": "If we add a 'phone_verified' boolean column to users table, which parts of the codebase need updates?",
  "model": "gpt-4",
  "mode": "think"
}
```

### Scenario 2: Documentation Generation

**Goal**: Auto-generate comprehensive docs

```bash
{
  "files": ["/path/to/src/models/**/*.java"],
  "db_queries": [
    "SHOW TABLES;",
    "SELECT table_name, column_name, column_type, column_key FROM information_schema.columns WHERE table_schema = 'myapp';"
  ],
  "db_dsn": "mysql://root@localhost:3306/myapp",
  "query": "Generate comprehensive API documentation covering models, database schema, and relationships",
  "model": "claude-sonnet-4",
  "mode": "mid",
  "output_file": "/path/to/docs/api-reference.md"
}
```

### Scenario 3: Code Review with Database Context

**Goal**: Review PR changes with schema awareness

```bash
{
  "files": [
    "/path/to/src/services/user-service.py",
    "/path/to/src/models/user.py"
  ],
  "db_queries": [
    "DESCRIBE users;",
    "SHOW INDEXES FROM users;",
    "SELECT COUNT(*) FROM users;"
  ],
  "db_dsn": "${DB_DSN}",
  "query": "Review this user service implementation for correctness, security, and performance",
  "model": "gpt-4",
  "mode": "think"
}
```

## Configuration Options

### Query Timeout

```bash
# Default: 30 seconds
{
  ...,
  "db_timeout": 60  # Increase for complex queries
}
```

### Result Set Limit

```bash
# Default: 10,000 rows
{
  ...,
  "db_max_rows": 5000  # Reduce to save tokens
}
```

### Output File

```bash
# Save analysis to file instead of returning in response
{
  ...,
  "output_file": "/path/to/analysis-report.md"
}
```

## Troubleshooting

### Error: Connection Failed

```
Database connection error: Authentication failed
```

**Solution**:
1. Verify DSN format: `mysql://user:password@host:3306/database`
2. Test connection manually: `mysql -h host -u user -p database`
3. Check firewall/network access
4. Verify credentials

### Error: Query Timeout

```
Query exceeded 30 second timeout
```

**Solutions**:
- Add WHERE clause to limit rows
- Add indexes to improve performance
- Increase timeout: `"db_timeout": 60`
- Split into multiple smaller queries

### Error: Write Operation Blocked

```
Query validation failed: Write operation 'INSERT' not permitted
```

**Solution**: Only use read operations:
- ✅ SELECT, SHOW, DESCRIBE, PRAGMA (SQL)
- ✅ find, findOne, aggregate, count (MongoDB)
- ❌ INSERT, UPDATE, DELETE, DROP, ALTER

### Warning: Results Truncated

```
Database results truncated: 50000 rows requested, 10000 included
```

**Solutions**:
- Add LIMIT clause to query: `SELECT * FROM users LIMIT 1000`
- Reduce file count to free up token budget
- Increase `db_max_rows` if needed: `"db_max_rows": 20000`
- Use WHERE clause for targeted analysis

### Error: Token Budget Exceeded

```
Combined content exceeds model token limit
```

**Solutions**:
- Reduce file patterns to specific directories
- Limit database queries to essential tables only
- Use LIMIT in SELECT queries
- Choose model with larger context window (e.g., grok-4-fast: 2M tokens)

## Best Practices

### 1. Start Small
Begin with specific files and targeted queries. Expand scope after verifying results.

### 2. Use LIMIT in Queries
Always add LIMIT to sample data queries to avoid token overflow.

```sql
-- Good
SELECT * FROM users LIMIT 100;

-- Risky
SELECT * FROM users;  -- May return millions of rows
```

### 3. Prioritize Files Over Database Results
File content gets priority in token budget. Database results truncated first if needed.

### 4. Use Specific Query Patterns

**Schema analysis**:
```sql
SHOW TABLES;
DESCRIBE table_name;
SHOW CREATE TABLE table_name;
```

**Data sampling**:
```sql
SELECT * FROM table LIMIT 100;
SELECT column, COUNT(*) FROM table GROUP BY column;
```

**Performance analysis**:
```sql
SHOW INDEXES FROM table;
EXPLAIN SELECT * FROM table WHERE condition;
```

### 5. Save Long Analyses to Files

For comprehensive reviews, use `output_file` to save results for later review.

### 6. Test Locally First

Before running against production databases, test with local/dev databases first.

### 7. Review Query Results

Check that database queries return expected data before running full analysis.

## Next Steps

- Read [data-model.md](./data-model.md) for entity details
- Check [contracts/consultation-tool.md](./contracts/consultation-tool.md) for full API spec
- Review examples in [HYBRID_CONSULTATION_FEATURE.md](../../docs/HYBRID_CONSULTATION_FEATURE.md)

## Support

For issues or questions:
1. Check error messages for actionable hints
2. Review troubleshooting section above
3. Test database connection independently
4. Verify query syntax for target database type
