"""Query validation and read-only enforcement."""

import re
from typing import Optional

# Comprehensive regex patterns for detecting write operations
WRITE_OPERATION_PATTERNS = [
    (r'\bINSERT\s+INTO\b', 'INSERT'),
    (r'\bUPDATE\s+\w+\s+SET\b', 'UPDATE'),
    (r'\bDELETE\s+FROM\b', 'DELETE'),
    (r'\bDROP\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA|TRIGGER|PROCEDURE|FUNCTION)\b', 'DROP'),
    (r'\bALTER\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b', 'ALTER'),
    (r'\bCREATE\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA|TRIGGER|PROCEDURE|FUNCTION)\b', 'CREATE'),
    (r'\bTRUNCATE\s+TABLE\b', 'TRUNCATE'),
    (r'\bREPLACE\s+INTO\b', 'REPLACE'),
    (r'\bMERGE\s+INTO\b', 'MERGE'),
    (r'\bGRANT\b', 'GRANT'),
    (r'\bREVOKE\b', 'REVOKE'),
    (r'\bRENAME\s+(TABLE|COLUMN)\b', 'RENAME'),
    (r'\bLOCK\s+TABLES\b', 'LOCK'),
    (r'\bUNLOCK\s+TABLES\b', 'UNLOCK'),
]

# Compiled patterns for performance
COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE), operation)
                     for pattern, operation in WRITE_OPERATION_PATTERNS]


def validate_query(query: str) -> tuple[bool, Optional[str]]:
    """Validate that query is read-only (no write operations).
    
    Performs comprehensive regex-based detection of write operations including:
    - Data modification: INSERT, UPDATE, DELETE, REPLACE, MERGE
    - Schema changes: CREATE, ALTER, DROP, RENAME
    - Table operations: TRUNCATE, LOCK
    - Permission changes: GRANT, REVOKE
    
    Args:
        query: SQL or database query to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if query is read-only
        - (False, error_message) if query contains write operations
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"

    # Normalize whitespace for better pattern matching
    normalized_query = ' '.join(query.split())
    
    # Allow SHOW CREATE TABLE/VIEW/DATABASE (read-only commands)
    if re.search(r'\bSHOW\s+CREATE\s+(TABLE|VIEW|DATABASE|SCHEMA|FUNCTION|PROCEDURE|TRIGGER)\b', 
                 normalized_query, re.IGNORECASE):
        return True, None

    # Check each pattern
    for pattern, operation in COMPILED_PATTERNS:
        if pattern.search(normalized_query):
            return False, (
                f"Query rejected: {operation} operation detected (write operation)\n"
                f"  Hint: Only read-only operations are allowed (SELECT, SHOW, DESCRIBE, EXPLAIN)\n"
                f"  Detected pattern: {operation}\n"
                f"  Query: {query[:100]}{'...' if len(query) > 100 else ''}"
            )

    return True, None


def is_safe_query(query: str) -> bool:
    """Quick check if query is safe (read-only).
    
    Args:
        query: Query to check
    
    Returns:
        True if query appears to be read-only
    """
    is_valid, _ = validate_query(query)
    return is_valid
