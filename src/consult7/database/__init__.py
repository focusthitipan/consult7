"""Database integration module for Consult7.

This module provides database connectivity and query execution capabilities
for hybrid consultations (files + database analysis).

Architecture:
- connection.py: DSN parsing and connection pooling
- validation.py: Query validation and read-only enforcement
- formatting.py: Result formatting for AI consumption
- adapters/: Database-specific implementations (MySQL, PostgreSQL, SQLite, MongoDB)
"""

from consult7.database.connection import ConnectionPool, parse_dsn
from consult7.database.formatting import format_database_results
from consult7.database.validation import validate_query

__all__ = [
    "ConnectionPool",
    "parse_dsn",
    "format_database_results",
    "validate_query",
]
