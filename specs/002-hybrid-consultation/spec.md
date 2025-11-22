# Feature Specification: Hybrid Consultation (Files + Database)

**Feature Branch**: `002-hybrid-consultation`  
**Created**: November 23, 2025  
**Status**: Draft  
**Input**: User description: "Add hybrid consultation feature supporting files and database analysis together in a single consultation with multi-database support"

## Clarifications

### Session 2025-11-23

- Q: Query Timeout Duration → A: 30 seconds
- Q: Database Connection Pooling Strategy → A: Shared connection pool with per-database management
- Q: Concurrent Consultation Handling → A: Sequential per DSN with shared file processing
- Q: Error Logging & Observability Level → A: Structured logging with query metadata
- Q: Maximum Database Result Set Size → A: 10,000 rows with configurable limit

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Code and Database Schema Analysis (Priority: P1)

A developer wants to verify that their application code matches the database schema to identify inconsistencies, missing fields, or type mismatches without manually cross-referencing files and database tables.

**Why this priority**: This is the core value proposition of the feature. It addresses the most common pain point developers face when maintaining applications - ensuring code and database remain in sync. Without this capability, developers must manually switch between code and database tools, which is error-prone and time-consuming.

**Independent Test**: Can be fully tested by providing a TypeScript User model file and executing `DESCRIBE users` query, then asking "Are there inconsistencies between the User model and database schema?" This delivers immediate value by identifying schema mismatches without any additional features.

**Acceptance Scenarios**:

1. **Given** a User model file in TypeScript and database connection with users table, **When** user runs consultation with both files and `DESCRIBE users` query, **Then** system returns analysis identifying fields present in code but missing in database, fields in database not used in code, and type mismatches
2. **Given** file patterns like `src/models/**/*.ts` and multiple database queries, **When** consultation is executed, **Then** all matched files and all query results are included in the AI analysis context
3. **Given** database query results totaling 100KB and code files totaling 500KB, **When** combined content is under model context limit, **Then** AI receives complete context for comprehensive analysis

---

### User Story 2 - Multi-Database Support for Diverse Tech Stacks (Priority: P2)

A team working with multiple database systems (MySQL for production, PostgreSQL for analytics, MongoDB for caching) needs to analyze code against different database types without changing tools or configurations.

**Why this priority**: Extends the core functionality to real-world scenarios where teams use multiple databases. While P1 delivers basic value, many production systems require multi-database support, making this critical for broader adoption.

**Independent Test**: Can be tested by configuring different DSN formats (MySQL, PostgreSQL, SQLite, MongoDB) and executing database-specific queries. Each database type should work independently with appropriate query syntax and result formatting.

**Acceptance Scenarios**:

1. **Given** DSN format `postgresql://user@host:5432/db`, **When** system parses the connection string, **Then** PostgreSQL adapter is selected and PostgreSQL-specific queries execute correctly
2. **Given** DSN format `mongodb://user:pass@host:27017/db`, **When** MongoDB queries like `db.users.findOne()` are executed, **Then** results are returned in native MongoDB document format
3. **Given** SQLite DSN `sqlite:///./app.db`, **When** consultation runs with SQLite-specific queries like `PRAGMA table_info(users)`, **Then** results display SQLite schema information correctly
4. **Given** MySQL DSN, **When** queries use `SHOW TABLES` and `DESCRIBE users`, **Then** system executes MySQL-specific syntax successfully

---

### User Story 3 - Safe Read-Only Database Access (Priority: P1)

A developer wants to analyze production database schema and sample data without risk of accidentally modifying or deleting data during consultation.

**Why this priority**: Safety is non-negotiable when working with production databases. This prevents catastrophic data loss and builds trust in the tool. Without this, the feature would be too risky to use in production environments.

**Independent Test**: Can be tested by attempting various write operations (INSERT, UPDATE, DELETE, DROP, ALTER) which should all be blocked with clear error messages, while SELECT and SHOW operations succeed.

**Acceptance Scenarios**:

1. **Given** database connection configured, **When** user provides query containing `INSERT INTO users ...`, **Then** system rejects the query with error message "Write operations not permitted - only read operations allowed"
2. **Given** valid SELECT query, **When** consultation executes, **Then** query returns results successfully
3. **Given** query containing `DROP TABLE users`, **When** validation occurs, **Then** system blocks execution and warns user about prohibited DDL operations
4. **Given** mixed queries including both SELECT and UPDATE, **When** validation runs, **Then** all queries are rejected if any contain write operations

---

### User Story 4 - Token Budget Management Across Files and Database (Priority: P2)

A user analyzing large codebases with extensive database results needs the system to intelligently manage token limits to prevent context overflow while maximizing useful content sent to the AI.

**Why this priority**: Essential for production use with large projects, but the feature can function with smaller projects first. Proper token management ensures the tool scales and prevents costly API errors from context overflow.

**Independent Test**: Can be tested by providing files and database queries that exceed model context limits, then verifying that system truncates database results first, warns the user, and stays within token budget.

**Acceptance Scenarios**:

1. **Given** model with 200K token context limit and content requiring 250K tokens, **When** system calculates budget, **Then** database results are truncated to fit within available space and user receives warning
2. **Given** file content consuming 80% of token budget, **When** database results are added, **Then** system calculates remaining space and applies appropriate limits to database queries
3. **Given** database query returning 10,000 rows, **When** result size would exceed token limit, **Then** system automatically applies LIMIT clause to reduce result set
4. **Given** combined content within token budget, **When** consultation proceeds, **Then** AI receives complete context without truncation

---

### User Story 5 - Flexible Consultation Modes (Priority: P3)

A developer wants to choose between analyzing files only, database only, or both together depending on their current task without changing tools.

**Why this priority**: Adds flexibility and convenience but not critical for core functionality. Users can still achieve their primary goals with P1/P2 features. This makes the tool more versatile for different workflows.

**Independent Test**: Can be tested by running three separate consultations: (1) files only with no database parameters, (2) database only with no files, (3) both files and database together. Each mode should work independently.

**Acceptance Scenarios**:

1. **Given** consultation request with files parameter but no database parameters, **When** executed, **Then** analysis proceeds with file content only (existing behavior)
2. **Given** consultation request with database queries and DSN but no files, **When** executed, **Then** analysis proceeds with database results only
3. **Given** consultation request with both files and database parameters, **When** executed, **Then** analysis includes both file content and database results
4. **Given** any consultation mode, **When** parameters are omitted, **Then** system validates requirements and provides clear error messages

---

### Edge Cases

- What happens when database connection fails during query execution? System should capture error, include it in the report, and continue with file analysis if files are provided.
- How does system handle queries that return empty result sets? Empty results should be clearly indicated in the output with message "Query returned 0 rows" rather than being omitted.
- What happens when file glob patterns match no files? System should warn user "Pattern matched 0 files" and proceed if database queries are provided, or fail if no content is available.
- How does system behave when database query times out? Timeout should be captured with message "Query exceeded timeout limit", and partial results or error should be included in analysis context.
- What happens when token budget is exceeded by files alone before adding database results? System should warn user that database results were omitted entirely and suggest reducing file count or query result sizes.
- How does system handle invalid SQL syntax? Query validation should catch syntax errors before execution and return actionable error messages.
- What happens when DSN format is incorrect or missing required components? DSN parser should validate format and provide specific error about missing components (e.g., "DSN missing database name").
- How does system handle binary or non-text query results? Binary content should be encoded or summarized appropriately rather than causing parsing errors.

## Requirements *(mandatory)*

### Functional Requirements

#### Core Consultation Features

- **FR-001**: System MUST accept file glob patterns and database query parameters in a single consultation request
- **FR-002**: System MUST execute database queries against configured database connection and retrieve results
- **FR-003**: System MUST combine file content and database query results into unified formatted content
- **FR-004**: System MUST support file-only consultations without database parameters (backward compatibility)
- **FR-005**: System MUST support database-only consultations without file parameters
- **FR-006**: System MUST clearly label and separate file content and database results in formatted output sent to AI

#### Database Connection and Query Execution

- **FR-007**: System MUST accept database DSN (Data Source Name) as configuration parameter in format `protocol://[user[:password]@]host[:port]/[database]`
- **FR-008**: System MUST parse DSN to automatically detect database type (MySQL, PostgreSQL, SQLite, MongoDB, etc.)
- **FR-009**: System MUST establish database connection using parsed DSN credentials and connection parameters
- **FR-010**: System MUST execute multiple SQL queries sequentially and collect all results
- **FR-011**: System MUST validate queries before execution to ensure only read operations are permitted (SELECT, SHOW, DESCRIBE, PRAGMA, etc.)
- **FR-012**: System MUST block write operations (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP) with clear error messages
- **FR-013**: System MUST format database query results as readable text suitable for AI analysis
- **FR-014**: System MUST handle database connection errors gracefully and include error details in consultation context
- **FR-015**: System MUST handle query execution errors and timeouts with informative messages

#### Multi-Database Support

- **FR-016**: System MUST support MySQL database connections and queries
- **FR-017**: System MUST support PostgreSQL database connections and queries
- **FR-018**: System MUST support SQLite database connections and queries
- **FR-019**: System MUST support MongoDB database connections and queries
- **FR-020**: System MUST automatically adapt query syntax validation based on detected database type
- **FR-021**: System MUST format query results according to database-specific native formats (e.g., MongoDB documents, SQL tables)
- **FR-022**: System MUST support database-specific query syntax (e.g., `SHOW TABLES` for MySQL, `information_schema` queries for PostgreSQL, `PRAGMA` for SQLite)

#### Token Budget Management

- **FR-023**: System MUST calculate total token usage for combined file content and database query results
- **FR-024**: System MUST respect model context window limits when preparing content
- **FR-025**: System MUST apply token safety factor (default 0.8) to prevent context overflow
- **FR-026**: System MUST reserve tokens for AI output (minimum 20% of available tokens)
- **FR-027**: System MUST truncate database query results first when combined content exceeds token budget
- **FR-028**: System MUST warn users when content has been truncated due to token limits
- **FR-029**: System MUST suggest actionable solutions when truncation occurs (e.g., "Reduce file count or limit query results")
- **FR-030**: System MUST automatically apply LIMIT clauses to database queries when result sets would exceed token budget

#### Configuration and Security

- **FR-031**: System MUST accept DSN from environment variable to avoid hardcoding credentials
- **FR-032**: System MUST support optional DSN parameter override at runtime
- **FR-033**: System MUST validate DSN format and provide specific error messages for missing or invalid components
- **FR-034**: System MUST not log or expose database credentials in error messages or output
- **FR-035**: System MUST enforce query timeout limits of 30 seconds to prevent long-running queries from blocking consultations
- **FR-036**: System MUST support SSL/TLS connection options for secure database connections when specified in DSN
- **FR-043**: System MUST implement connection pooling with per-database pool management to optimize resource usage across concurrent requests
- **FR-044**: System MUST limit maximum database result set to 10,000 rows per query with configurable override capability
- **FR-045**: System MUST process concurrent consultations sequentially per database DSN while sharing file processing to prevent race conditions

#### Output and Reporting

- **FR-037**: System MUST include clear section headers separating files and database results in formatted output
- **FR-038**: System MUST display file discovery summary (count, patterns matched)
- **FR-039**: System MUST display database query summary (query count, result row counts)
- **FR-040**: System MUST report total content size and estimated token usage
- **FR-041**: System MUST indicate when database results or files were truncated or omitted
- **FR-042**: System MUST include query execution metadata (execution time, row counts, errors)
- **FR-046**: System MUST generate structured logs containing query execution details (duration, rows returned, connection status, truncation events) for troubleshooting and monitoring
- **FR-047**: System MUST not include database credentials, sensitive data values, or user-submitted queries in logs

### Key Entities

- **Consultation Request**: Represents a single analysis request containing file patterns, database queries, DSN, user query, and model configuration
- **Database Connection**: Represents active connection to database system with DSN, connection parameters, database type, and connection state
- **Query Result**: Represents output from executed database query including result data, row count, execution time, and error information if applicable
- **Content Bundle**: Represents unified formatted content combining file contents and database results ready for AI analysis, including token count, truncation status, and section separators
- **Database Adapter**: Represents database-specific query handler for each supported database type (MySQL, PostgreSQL, SQLite, MongoDB) with query validation rules and result formatting logic

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can analyze code files and database schema together in a single consultation without switching tools
- **SC-002**: System successfully executes read-only database queries against production databases without risk of data modification
- **SC-003**: System supports at least 4 major database types (MySQL, PostgreSQL, SQLite, MongoDB) with appropriate query syntax and result formatting
- **SC-004**: Combined file and database content stays within model token limits in 95% of typical use cases (projects with <100 files and <1000 rows of results)
- **SC-005**: Developers receive actionable analysis identifying schema inconsistencies, missing fields, type mismatches, and data quality issues
- **SC-006**: System processes consultations with database queries within 5 seconds of file-only consultation time (excluding database query execution time)
- **SC-007**: Token budget management prevents context overflow errors in 100% of consultations by automatically truncating content when necessary
- **SC-008**: Existing file-only consultation workflows continue to work without modification (100% backward compatibility)
- **SC-009**: Database connection errors are caught and reported with actionable error messages in 100% of cases
- **SC-010**: Write operations (INSERT, UPDATE, DELETE, DDL) are blocked with clear error messages in 100% of attempts
- **SC-011**: Query execution completes or times out within 30 seconds in 100% of cases, preventing indefinite blocking
- **SC-012**: Concurrent consultations are handled safely without race conditions by enforcing sequential processing per database DSN
