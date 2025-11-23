"""Abstract base class for database adapters."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseAdapter(ABC):
    """Abstract base class for database-specific adapters.
    
    Each database type (MySQL, PostgreSQL, SQLite, MongoDB) implements
    this interface to provide consistent query execution and formatting.
    """

    def __init__(self, dsn: str, timeout: float, max_rows: int):
        """Initialize adapter with connection parameters.
        
        Args:
            dsn: Database connection string
            timeout: Query execution timeout in seconds
            max_rows: Maximum number of rows to return
        """
        self.dsn = dsn
        self.timeout = timeout
        self.max_rows = max_rows
        self.connection: Optional[Any] = None

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """Validate that query is read-only.
        
        Args:
            query: Query to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute read-only query and return results.
        
        Args:
            query: SQL or database query to execute
        
        Returns:
            List of result rows (each row is a dictionary)
        
        Raises:
            TimeoutError: If query exceeds timeout
            ValueError: If query is not read-only
            RuntimeError: If query execution fails
        """
        pass

    @abstractmethod
    def format_result(self, results: list[dict[str, Any]], query: str) -> str:
        """Format query results for AI consumption.
        
        Args:
            results: Query results
            query: Original query
        
        Returns:
            Formatted string suitable for LLM input
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection and release resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
