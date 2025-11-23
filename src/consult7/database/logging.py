"""Structured logging for database operations."""

import hashlib
import json
import logging
import time
from typing import Optional

# Configure logger for database operations
db_logger = logging.getLogger("consult7.database")


def sanitize_dsn(dsn: str) -> str:
    """Sanitize DSN by removing credentials.
    
    Args:
        dsn: Database connection string
    
    Returns:
        DSN with credentials masked
    """
    # Simple approach: Replace everything between :// and @
    import re
    return re.sub(r'://([^@]+)@', '://***:***@', dsn)


def hash_query(query: str) -> str:
    """Generate hash of query for logging (deduplication).
    
    Args:
        query: SQL query
    
    Returns:
        SHA256 hash of query (first 16 characters)
    """
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def log_connection(dsn: str, success: bool, error: Optional[str] = None, duration: float = 0.0) -> None:
    """Log database connection attempt.
    
    Args:
        dsn: Database connection string (will be sanitized)
        success: Whether connection succeeded
        error: Error message if failed
        duration: Connection time in seconds
    """
    log_data = {
        "event": "database_connection",
        "dsn": sanitize_dsn(dsn),
        "success": success,
        "duration_seconds": round(duration, 3),
    }

    if error:
        log_data["error"] = error

    if success:
        db_logger.info(json.dumps(log_data))
    else:
        db_logger.error(json.dumps(log_data))


def log_query_execution(
    query: str,
    dsn: str,
    success: bool,
    row_count: int = 0,
    duration: float = 0.0,
    error: Optional[str] = None,
    blocked: bool = False
) -> None:
    """Log query execution with metadata.
    
    Security audit: Blocked write attempts are logged at WARNING level
    with query hash and operation type for security monitoring.
    
    Args:
        query: SQL query (will be hashed)
        dsn: Database connection string (will be sanitized)
        success: Whether query executed successfully
        row_count: Number of rows returned
        duration: Query execution time in seconds
        error: Error message if failed
        blocked: Whether query was blocked (write operation)
    """
    log_data = {
        "event": "query_execution",
        "query_hash": hash_query(query),
        "query_preview": query[:100] + ("..." if len(query) > 100 else ""),
        "dsn": sanitize_dsn(dsn),
        "success": success,
        "blocked": blocked,
        "row_count": row_count,
        "duration_seconds": round(duration, 3),
        "timestamp": time.time(),
    }

    if error:
        log_data["error"] = error

    # Security audit: Log blocked operations for monitoring
    if blocked:
        # Extract operation type from error message
        if error and any(op in error for op in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]):
            for op in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]:
                if op in error:
                    log_data["blocked_operation"] = op
                    break
        db_logger.warning(json.dumps(log_data))
    elif success:
        db_logger.info(json.dumps(log_data))
    else:
        db_logger.error(json.dumps(log_data))


def log_pool_operation(dsn: str, operation: str, pool_size: int, active_connections: int) -> None:
    """Log connection pool operations.
    
    Args:
        dsn: Database connection string (will be sanitized)
        operation: Operation type (acquire, release, close_all)
        pool_size: Maximum pool size
        active_connections: Current number of active connections
    """
    log_data = {
        "event": "connection_pool",
        "dsn": sanitize_dsn(dsn),
        "operation": operation,
        "pool_size": pool_size,
        "active_connections": active_connections,
    }

    db_logger.debug(json.dumps(log_data))


class QueryTimer:
    """Context manager for timing query execution."""

    def __init__(self):
        self.start_time: float = 0.0
        self.duration: float = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
