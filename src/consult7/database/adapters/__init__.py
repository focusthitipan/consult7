"""Database adapters for different database types."""

from .base import BaseAdapter
from .mysql import MySQLAdapter
from .postgresql import PostgreSQLAdapter
from .sqlite import SQLiteAdapter
from .mongodb import MongoDBAdapter

__all__ = [
    "BaseAdapter",
    "MySQLAdapter",
    "PostgreSQLAdapter",
    "SQLiteAdapter",
    "MongoDBAdapter",
]


def create_adapter(
    protocol: str,
    host: str,
    port: int,
    database: str,
    username: str = None,
    password: str = None,
    timeout: float = 30.0,
    max_rows: int = 10_000,
) -> BaseAdapter:
    """Factory function to create appropriate adapter based on protocol.

    Args:
        protocol: Database protocol (mysql, postgresql, sqlite, mongodb)
        host: Database host (or file path for SQLite)
        port: Database port
        database: Database name
        username: Optional username
        password: Optional password
        timeout: Query timeout in seconds
        max_rows: Maximum rows per query

    Returns:
        Appropriate database adapter instance

    Raises:
        ValueError: If protocol is not supported
    """
    if protocol == "mysql":
        # MySQLAdapter uses DSN format
        auth = f"{username}:{password}@" if username else ""
        # Only include database in DSN if specified
        if database:
            dsn = f"mysql://{auth}{host}:{port}/{database}"
        else:
            dsn = f"mysql://{auth}{host}:{port}"
        return MySQLAdapter(
            dsn=dsn,
            timeout=timeout,
            max_rows=max_rows,
        )
    elif protocol == "postgresql":
        return PostgreSQLAdapter(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            timeout=timeout,
            max_rows=max_rows,
        )
    elif protocol == "sqlite":
        # For SQLite, host is the database path
        return SQLiteAdapter(
            database_path=host,  # SQLite uses host as file path
            timeout=timeout,
            max_rows=max_rows,
        )
    elif protocol == "mongodb":
        return MongoDBAdapter(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            timeout=timeout,
            max_rows=max_rows,
        )
    else:
        raise ValueError(
            f"Unsupported database protocol: {protocol}\n"
            f"  Supported protocols: mysql, postgresql, sqlite, mongodb"
        )
