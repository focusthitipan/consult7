# Hybrid Consultation Feature: Files + Database

## Overview

Consult7 now supports analyzing **files and database queries together** in a single consultation. This unified approach allows AI to understand the relationship between your code and database structure, providing more comprehensive and accurate analysis.

## What It Does

### Before (File Only)
```
User Query
    ↓
[Process Files]
    ↓
AI Analyzes Code Only
```

### After (File + Database)
```
User Query
    ↓
┌─ [Process Files] ────┐
├─ [Execute DB Queries]┤ → [Unified Content] → AI Analyzes Code + DB
└────────────────────┘
```

## Key Features

### 1. **Unified Analysis**
- AI sees both code and database context in a single analysis
- Understands relationships between code logic and database structure
- Provides comprehensive recommendations based on full context

### 2. **Flexible Input**
- Analyze files only (existing functionality)
- Analyze database queries only (new)
- Analyze files + database together (new)

### 3. **Smart Token Management**
- Automatically calculates optimal budget for file + database content
- Respects model context window limits
- Prioritizes content intelligently when space is limited

### 4. **Backward Compatible**
- Existing file-only workflows work unchanged
- Database parameters are optional
- No breaking changes to current API

## Use Cases

### 1. Code + Schema Validation
```
Query: "Check if the user model matches the database schema"
Files: src/**/*.ts (User model implementation)
DB: SHOW TABLES, DESCRIBE users (Database structure)
Result: Identifies mismatches, missing fields, inconsistencies
```

### 2. Data Quality & Code Logic
```
Query: "Analyze data patterns and code that processes them"
Files: src/services/**/*.py (Business logic)
DB: SELECT * FROM orders LIMIT 100 (Sample data)
Result: Spots edge cases, data validation issues, potential bugs
```

### 3. API Implementation Review
```
Query: "Verify endpoint implementation against database design"
Files: src/routes/**/*.ts (API endpoints)
DB: DESCRIBE orders, SHOW INDEXES (Database design)
Result: Validates queries, identifies N+1 problems, performance issues
```

### 4. Migration Planning
```
Query: "Assess impact of database changes on code"
Files: src/**/*.py (Application code)
DB: Current schema and proposed schema
Result: Predicts breaking changes, suggests code updates
```

### 5. Documentation Generation
```
Query: "Generate comprehensive documentation"
Files: src/**/*.ts (Implementation)
DB: SHOW TABLES, DESCRIBE * (Database schema)
Result: Auto-generates documentation covering code & data
```

## How It Works

### 1. Input
User provides:
- **Files**: Glob patterns for code files
- **Database Queries**: SQL queries to execute
- **Database Connection**: DSN (Data Source Name)
- **Query**: Analysis question for AI

### 2. Processing
Consult7:
1. Discovers files using glob patterns
2. Executes database queries
3. Formats both as readable content sections
4. Estimates total token usage
5. Ensures content fits model's context window

### 3. AI Analysis
The language model receives:
- Formatted file contents (clearly labeled)
- Database query results (clearly labeled)
- Unified query asking for analysis
- Full context to provide comprehensive insights

### 4. Output
AI delivers analysis covering:
- Code structure and patterns
- Database schema and relationships
- How they interact and relate
- Identified issues and recommendations

## Content Organization

When consult7 sends content to AI, it's organized clearly:

```
═══════════════════════════════════════
FILE SIZE BUDGET
═══════════════════════════════════════
File Size Budget: 4,000,000 bytes (~1M tokens)
Files Found: 12

═══════════════════════════════════════
FILES TO PROCESS
═══════════════════════════════════════
src/
  - models.ts
  - services.ts
  - routes.ts
...

File Contents:
───────────────────────────────────────
File: src/models.ts
───────────────────────────────────────
[file content...]

═══════════════════════════════════════
DATABASE RESULTS
═══════════════════════════════════════
Query 1: SHOW TABLES;
───────────────────────────────────────
[query results...]

Query 2: DESCRIBE users;
───────────────────────────────────────
[query results...]

═══════════════════════════════════════
Total content: 850KB from 12 files + 2 DB queries
Estimated tokens: ~175,000 (Model limit: 200,000)

Query: Analyze code structure and database schema relationships
```

## Configuration

### Database Connection
```json
{
  "consult7": {
    "command": "consult7",
    "args": ["github-copilot", "oauth:"],
    "env": {
      "DB_DSN": "${DB_DSN}"
    }
  }
}
```

Set environment variable:
```bash
$env:DB_DSN = "mysql://root:password@localhost:3306/database"
```

### DSN Format
```
mysql://[user[:password]@]host[:port]/[database]
postgresql://[user[:password]@]host[:port]/[database]
```

## Multi-Database Support

Consult7 supports **multiple database systems** via a unified interface. The feature automatically detects the database type from the DSN and adapts query execution accordingly.

### Supported Databases

| Database | DSN Format | Status |
|----------|-----------|--------|
| **MySQL** | `mysql://user:pass@host:3306/db` | ✅ Full Support |
| **PostgreSQL** | `postgresql://user:pass@host:5432/db` | ✅ Full Support |
| **SQLite** | `sqlite:///./database.db` | ✅ Full Support |
| **MongoDB** | `mongodb://user:pass@host:27017/db` | ✅ Full Support |
| **MariaDB** | `mysql://user:pass@host:3306/db` | ✅ Full Support |
| **TiDB** | `mysql://user:pass@host:4000/db` | ✅ Full Support |
| **CockroachDB** | `postgresql://user:pass@host:26257/db` | ✅ Full Support |
| **Other dbhub-supported** | Database-specific format | ✅ Full Support |

### How Database Auto-Detection Works

Consult7 automatically detects the database type from the DSN scheme:

1. **Parse DSN scheme**: Extract the protocol prefix (mysql, postgresql, sqlite, mongodb)
2. **Select adapter**: Choose the appropriate query handler for that database
3. **Adapt queries**: Normalize SQL queries for the specific database syntax
4. **Format results**: Present results in the native format for that database

Example detection:
```
DSN: postgresql://user@localhost:5432/mydb
     ↓
Detected: PostgreSQL
     ↓
Adapter: PostgreSQL (supports standard SQL)
     ↓
Query: SELECT * FROM information_schema.tables;
```

### Database-Specific Examples

#### PostgreSQL Analysis
```bash
$env:DB_DSN = "postgresql://user:pass@localhost:5432/ecommerce"

consult7 github-copilot oauth: \
  --files "src/**/*.py" \
  --db-queries "SELECT table_name FROM information_schema.tables;" \
                "SELECT * FROM pg_indexes;" \
  --db-dsn "${DB_DSN}" \
  --query "Analyze Python code against PostgreSQL schema and indexes"
```

**What AI sees**:
- Python implementation files
- PostgreSQL table structure
- Index strategy and performance hints

#### SQLite Analysis
```bash
$env:DB_DSN = "sqlite:///./app.db"

consult7 github-copilot oauth: \
  --files "src/**/*.rs" \
  --db-queries "SELECT name FROM sqlite_master WHERE type='table';" \
                "PRAGMA table_info(users);" \
  --db-dsn "${DB_DSN}" \
  --query "Verify Rust implementation matches SQLite schema"
```

**What AI sees**:
- Rust code and types
- SQLite table definitions
- Column constraints and data types

#### MongoDB Analysis
```bash
$env:DB_DSN = "mongodb://user:pass@localhost:27017/myapp"

consult7 github-copilot oauth: \
  --files "src/**/*.js" \
  --db-queries "db.users.findOne();" \
                "db.orders.findOne();" \
  --db-dsn "${DB_DSN}" \
  --query "Analyze Node.js code against MongoDB document structure"
```

**What AI sees**:
- Node.js application code
- Sample MongoDB documents
- Document structure and relationships

#### MySQL Analysis
```bash
$env:DB_DSN = "mysql://root:pass@localhost:3306/myapp"

consult7 github-copilot oauth: \
  --files "src/models/**/*.go" \
  --db-queries "SHOW TABLES;" \
                "SHOW CREATE TABLE users;" \
                "SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS;" \
  --db-dsn "${DB_DSN}" \
  --query "Review Go ORM models against MySQL database design"
```

**What AI sees**:
- Go struct definitions and ORM tags
- MySQL table schemas
- Complete column specifications

### Query Syntax Variations

Different databases support different query syntax. Consult7 handles these variations:

#### Schema Discovery
```sql
-- PostgreSQL
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- MySQL
SHOW TABLES;

-- SQLite
SELECT name FROM sqlite_master WHERE type='table';

-- MongoDB
db.getCollectionNames();
```

Consult7 intelligently translates or adapts queries based on the detected database type.

#### Data Inspection
```sql
-- PostgreSQL
SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users';

-- MySQL
DESCRIBE users;

-- SQLite
PRAGMA table_info(users);

-- MongoDB
db.users.findOne();
```

### Content Formatting by Database Type

Output formatting adapts to each database's native result format:

#### PostgreSQL Results
```
═══════════════════════════════════════
DATABASE: PostgreSQL
═══════════════════════════════════════
Query: SELECT table_name FROM information_schema.tables;
───────────────────────────────────────
     table_name
─────────────────
 users
 orders
 products
```

#### MongoDB Results
```
═══════════════════════════════════════
DATABASE: MongoDB
═══════════════════════════════════════
Query: db.users.findOne();
───────────────────────────────────────
{
  "_id": ObjectId("..."),
  "name": "Alice",
  "email": "alice@example.com",
  "created_at": ISODate("2024-01-15T10:30:00Z")
}
```

#### SQLite Results
```
═══════════════════════════════════════
DATABASE: SQLite
═══════════════════════════════════════
Query: SELECT name FROM sqlite_master WHERE type='table';
───────────────────────────────────────
name
────────
users
orders
products
```

### Token Budget Across Databases

Token usage calculation remains consistent across all database types:

- **File content**: Counted same way
- **Database results**: Counted based on formatted output size
- **Total budget**: Respects model context window for any database
- **Overflow handling**: Database results truncated first if needed

Example:
```
Available tokens: 200,000
File content: 80,000 tokens
Database results: 60,000 tokens
Reserve for output: 40,000 tokens
Status: ✅ Within budget
```

### Security & Connection Strings

#### Best Practices for Multi-Database DSNs

```bash
# ✅ Good: Environment variables with no password
$env:DB_DSN = "postgresql://user@localhost:5432/db"
$env:DB_PASSWORD = "secure_password"  # Separate env var

# ✅ Best: Connection pooling with auth proxy
$env:DB_DSN = "postgresql://user@pgbouncer:6432/db"

# ❌ Avoid: Hardcoded credentials
--db-dsn "mysql://root:password@localhost:3306/db"
```

#### Database-Specific Security Notes

**PostgreSQL**: Use SSL/TLS for remote connections
```
postgresql://user@host:5432/db?sslmode=require
```

**MySQL**: Use SSL for network traffic
```
mysql://user@host:3306/db?tls=true
```

**MongoDB**: Use authentication and encryption
```
mongodb://user:pass@host:27017/db?authSource=admin&ssl=true
```

**SQLite**: Ensure file permissions are restricted
```
sqlite:///./database.db  # Ensure only app can read
```

## Benefits

| Aspect | Benefit |
|--------|---------|
| **Accuracy** | AI understands full context, reduces assumptions |
| **Completeness** | Analysis covers code AND data perspectives |
| **Speed** | Single analysis instead of switching between tools |
| **Maintenance** | Easier to spot inconsistencies and issues |
| **Documentation** | More comprehensive and accurate documentation |
| **Learning** | Better understanding of code-data relationships |

## Example Scenario

### Request
```bash
consult7 github-copilot oauth: \
  --files "src/**/*.ts" \
  --db-queries "SHOW TABLES;" "DESCRIBE users;" "SELECT COUNT(*) FROM users;" \
  --db-dsn "${DB_DSN}" \
  --query "Are there any inconsistencies between the User model and database schema?"
```

### What AI Sees
- User model implementation (TypeScript)
- Database table structure (DESCRIBE output)
- Data statistics (SELECT COUNT)
- Relationships and constraints

### What AI Provides
- List of fields in code but not in database
- List of database fields not used in code
- Type mismatches (number vs string, etc.)
- Missing validations
- Unused columns
- Performance concerns
- Recommendations for alignment

## Scope Limitations

### What It Supports
- ✅ SQL SELECT queries (read-only)
- ✅ SHOW statements
- ✅ DESCRIBE statements
- ✅ Multiple queries in one consultation
- ✅ Files and database together
- ✅ Database only (no files)
- ✅ Files only (existing mode)

### What It Doesn't Support
- ❌ INSERT, UPDATE, DELETE queries (write operations)
- ❌ DDL changes (CREATE, ALTER, DROP)
- ❌ Dynamic queries based on application input
- ❌ Real-time data streaming

### Query Validation
- Queries must be valid SQL
- Write operations are blocked
- Query results are limited to prevent token overflow
- Large result sets are truncated with warning

## Token Budget

The feature respects model context window constraints:

### Calculation
```
Available Tokens = Model Context Length × Safety Factor (0.8)
Reserved for Output = Available Tokens × 0.2
Available for Input = Available Tokens × 0.8

Input Space = Files + Database Results
```

### Auto-Adjustment
If combined content exceeds budget:
1. Database results reduced first (LIMIT applied)
2. File list pruned if necessary
3. User receives warning with suggestions

## Backward Compatibility

### Existing Workflows Unchanged
- File-only consultations work identically
- Database parameters are completely optional
- No changes required to existing configurations
- All current features work as before

### Opting In
Use the feature by simply adding:
- `--db-queries` parameter
- `--db-dsn` parameter

Without these, consult7 works exactly as before.

## Performance Considerations

### Speed Impact
- Negligible for file analysis (same as before)
- Database query execution adds:
  - Network latency to database
  - Query execution time
  - Typical: < 1-2 seconds

### Token Usage
- Efficient formatting of database results
- Smart truncation prevents token waste
- Content prioritization based on importance

## Security & Privacy

### Credential Management
- Database credentials stored in environment variables
- Never hardcoded in configuration files
- Encrypted storage for sensitive information

### Data Handling
- Database query results are sent to LLM
- Results are read-only (SELECT queries only)
- No data modifications possible
- Consider sensitivity when selecting queries

### Query Safety
- Write operations prevented
- SQL injection protections
- Query validation before execution

## Integration Points

The feature integrates seamlessly with:
- Existing file analysis capabilities
- Current token management system
- All supported LLM providers
- MCP client configurations

No architectural changes required in core systems.

---

**Version**: 1.0  
**Status**: Design Complete  
**Release**: Planned for upcoming release
