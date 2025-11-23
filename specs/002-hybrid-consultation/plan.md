# Implementation Plan: Hybrid Consultation (Files + Database)

**Branch**: `002-hybrid-consultation` | **Date**: November 23, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-hybrid-consultation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add hybrid consultation capability enabling AI analysis of code files and database content together in a single consultation. The feature extends consult7's existing file-only analysis to support database queries, combining results into unified content for comprehensive code-database schema validation, data quality analysis, and API implementation review. Core requirements include multi-database support (MySQL, PostgreSQL, SQLite, MongoDB), read-only query enforcement, intelligent token budget management across files and database results, and 100% backward compatibility with existing file-only workflows.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: 
- MCP SDK 1.9.4+ (Model Context Protocol)
- httpx (async HTTP client with timeout support)
- Database drivers: pymysql, psycopg2, sqlite3 (stdlib), pymongo
- Existing: token_utils, file_processor, consultation modules

**Storage**: 
- OAuth tokens: AES-256-GCM encrypted files (~/.consult7/, ~/.gemini/, ~/.qwen/)
- No persistent database storage (stateless consultations)
- Database connections: Transient connection pooling per DSN

**Testing**: 
- pytest (unit tests for query validation, token budget calculation)
- Integration tests via MCP client (file + database combinations)
- CLI --test flag validation (connection, query execution, error handling)

**Target Platform**: Cross-platform MCP server (Windows, macOS, Linux)

**Project Type**: Single project (Python MCP server extending existing consult7 architecture)

**Performance Goals**: 
- Query timeout: 30 seconds (configurable)
- File + DB consultation overhead: <5 seconds beyond file-only time
- Connection pooling: Reuse connections across sequential queries per DSN
- Result set limit: 10,000 rows (configurable)

**Constraints**: 
- Stateless operations (Constitution Principle I)
- Read-only database access (no INSERT/UPDATE/DELETE/DDL)
- Dynamic token budget (Constitution Principle III)
- Absolute paths only (Constitution Principle IV)
- Backward compatibility: 100% with existing file-only consultations
- Token safety factor: 0.8 (reserve 20% buffer)

**Scale/Scope**: 
- Support 4+ database types (MySQL, PostgreSQL, SQLite, MongoDB)
- Handle combined content: <100 files + <10K rows typical use case
- Concurrent consultations: Sequential per DSN, shared file processing
- Model context windows: 128K-2M tokens (dynamic adaptation)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Stateless Operations
✅ **PASS** - Database consultation design maintains stateless architecture:
- Each consultation accepts DSN, queries, files as parameters
- No shared state between consultations
- Connection pooling managed per-DSN, not globally shared across calls
- Each `consultation_impl()` invocation is fully self-contained

### Principle II: Provider Abstraction
✅ **PASS** - Feature extends existing provider architecture without modifications:
- Database integration separate from LLM provider layer
- Works with all existing providers (OpenRouter, Gemini CLI, Qwen Code, GitHub Copilot)
- No provider-specific database logic

### Principle III: Dynamic Token Management
✅ **PASS** - Database results integrated into existing dynamic token calculation:
- Reuses `get_model_context_info()` → `calculate_max_file_size()` workflow
- Database result size counted toward total token budget
- Truncation applies to database results first when budget exceeded
- No hardcoded limits for combined file + database content

### Principle IV: Absolute Paths Only
✅ **PASS** - File patterns follow existing absolute path requirements:
- Database DSN is URL format (not file path)
- File glob patterns unchanged from existing validation
- No relative path introduction

### Principle V: Actionable Error Messages
✅ **PASS** - All database errors include actionable hints:
- DSN format errors: Include correct format examples
- Query validation errors: Specify which operation blocked (INSERT/UPDATE/DELETE) with reason
- Connection errors: Include DSN troubleshooting hints
- Timeout errors: Suggest query optimization or timeout adjustment

### Principle VI: Test-Before-Deploy
✅ **PASS** - Testing strategy includes:
- Unit tests for query validation logic
- Integration tests with test databases
- Manual testing protocol: test consultations with sample databases
- Error handling validation for connection failures, timeouts, invalid queries

### Additional Compliance

**Security Standards**:
✅ DSN accepted via environment variable or runtime parameter
✅ No DSN credentials logged or exposed in errors
✅ Read-only enforcement prevents data modification

**Performance Standards**:
✅ 30-second query timeout (configurable)
✅ Connection pooling reduces overhead
✅ 10,000 row limit prevents token budget overflow

**Development Workflow**:
✅ TDD approach: query validation tests → implementation
✅ Integration testing with multiple database types
✅ CLI testing for each supported database

### Gate Status: ✅ ALL GATES PASSED

No constitution violations. Feature aligns with all core principles and technical constraints. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/consult7/
├── __init__.py
├── __main__.py
├── server.py              # MCP server setup (extend tool_definitions)
├── consultation.py        # Main entry point (extend consultation_impl)
├── file_processor.py      # Existing file handling (unchanged)
├── token_utils.py         # Existing token calculation (extend for DB results)
├── tool_definitions.py    # MCP tool schemas (extend consultation tool)
├── constants.py           # Add database-related constants
├── database/              # NEW: Database integration module
│   ├── __init__.py
│   ├── connection.py      # Connection pooling, DSN parsing
│   ├── validation.py      # Query validation (read-only enforcement)
│   ├── formatting.py      # Result formatting for AI consumption
│   └── adapters/
│       ├── __init__.py
│       ├── base.py        # BaseAdapter abstract class
│       ├── mysql.py       # MySQLAdapter implementation
│       ├── postgresql.py  # PostgreSQLAdapter implementation
│       ├── sqlite.py      # SQLiteAdapter implementation
│       └── mongodb.py     # MongoDBAdapter implementation
└── providers/             # Existing provider modules (unchanged)
    ├── __init__.py
    ├── base.py
    ├── openrouter.py
    ├── gemini_cli.py
    ├── qwen_code.py
    └── github_copilot.py

tests/
├── unit/
│   ├── test_database_connection.py
│   ├── test_query_validation.py
│   ├── test_dsn_parsing.py
│   ├── test_result_formatting.py
│   └── test_token_budget.py
└── integration/
    ├── test_mysql_integration.py
    ├── test_postgresql_integration.py
    ├── test_sqlite_integration.py
    ├── test_mongodb_integration.py
    ├── test_hybrid_consultation.py
    └── fixtures/
        ├── test_databases.sql
        └── sample_data.json
```

**Structure Decision**: Single Python project extending existing consult7 architecture

**Key Design Choices**:
1. **New `database/` module**: Isolated database functionality, easy to test independently
2. **Adapter pattern**: Each database type has dedicated adapter implementing `BaseAdapter`
3. **Minimal changes to existing code**: Only extend `consultation.py`, `tool_definitions.py`, `token_utils.py`
4. **Separate validation module**: Query validation logic isolated for security auditing
5. **Test structure mirrors implementation**: Unit tests for each module, integration tests per database type

## Complexity Tracking

> **No constitution violations detected. This section intentionally left empty.**

All design decisions align with constitution principles. No complexity justifications needed.

---

## Phase 2: Implementation Breakdown

**Note**: Detailed task breakdown will be generated by `/speckit.tasks` command.

**High-Level Implementation Phases**:

### Phase 2.1: Database Core Infrastructure
- Implement DSN parsing and validation
- Create BaseAdapter abstract class
- Implement connection pooling (stdlib Queue)
- Add structured logging infrastructure

### Phase 2.2: Database Adapters
- Implement MySQLAdapter
- Implement PostgreSQLAdapter
- Implement SQLiteAdapter
- Implement MongoDBAdapter
- Unit tests for each adapter

### Phase 2.3: Query Validation & Security
- Implement regex-based write operation detection
- Add database-specific read-only mode enforcement
- Error message formatting with actionable hints
- Security audit of validation logic

### Phase 2.4: Result Formatting & Token Management
- Implement result formatting (plain text with separators)
- Extend token estimation for database results
- Implement truncation logic (DB results first)
- Add warning generation for truncated content

### Phase 2.5: Integration with Existing Consultation Flow
- Extend `consultation_impl()` to accept database parameters
- Integrate database execution with file processing
- Update `tool_definitions.py` with new parameters
- Maintain backward compatibility

### Phase 2.6: Testing & Validation
- Unit tests for all new modules (target: 90%+ coverage)
- Integration tests with test databases
- CLI testing with real database connections
- Error handling validation
- Performance testing (connection pooling, timeout enforcement)

### Phase 2.7: Documentation & Deployment
- Update README with database feature docs
- Update copilot-instructions.md with architecture details
- Create migration guide for users
- Update MCP client configuration examples

---

## Definition of Done

### Code Complete
- [x] All constitution principles validated
- [ ] All modules implemented per data model
- [ ] Unit tests written (90%+ coverage target)
- [ ] Integration tests passing for all 4 database types
- [ ] Error messages include actionable hints
- [ ] Structured logging in place

### Testing Complete
- [ ] CLI `--test` flag works for database connections
- [ ] Backward compatibility verified (files-only consultations unchanged)
- [ ] Token budget management tested with overflow scenarios
- [ ] Query validation blocks all write operations
- [ ] Connection pooling tested under concurrent load
- [ ] Timeout enforcement tested

### Documentation Complete
- [ ] quickstart.md updated with examples
- [ ] API contract documented in contracts/
- [ ] copilot-instructions.md updated
- [ ] README updated with database feature section
- [ ] Migration guide created

### Quality Gates
- [ ] Ruff linting passes (`ruff check .`)
- [ ] Type hints added (mypy compatible)
- [ ] No security vulnerabilities (Bandit scan)
- [ ] Constitution compliance verified
- [ ] PR reviewed and approved

---

## Risk Assessment

### Low Risk
- ✅ Backward compatibility (all database params optional)
- ✅ Constitution compliance (no violations)
- ✅ Technology choices (proven libraries, stdlib-first)

### Medium Risk
- ⚠️ **Query validation completeness**: Regex may miss edge cases
  - **Mitigation**: Defense in depth (regex + database read-only mode)
  - **Validation**: Security audit of validation logic, extensive test cases

- ⚠️ **Token estimation accuracy**: Database results may have different token density
  - **Mitigation**: Use same estimation as files (~4 chars/token), apply safety factor
  - **Validation**: Test with real LLM calls, monitor truncation rates

### Monitoring Plan
- Track database connection failures (log analysis)
- Monitor token budget overflow frequency
- Measure query execution times (P50, P95, P99)
- Count validation rejections by query type
