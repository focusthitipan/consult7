"""MySQL database adapter implementation."""

import pymysql
from typing import Any, Optional

from consult7.database.adapters.base import BaseAdapter
from consult7.database.formatting import format_database_results
from consult7.database.validation import validate_query
from consult7.database.logging import log_connection, log_query_execution, QueryTimer


class MySQLAdapter(BaseAdapter):
    """MySQL-specific database adapter using pymysql driver."""

    def __init__(self, dsn: str, timeout: float, max_rows: int):
        """Initialize MySQL adapter.
        
        Args:
            dsn: MySQL connection string (mysql://user:pass@host:port/database)
            timeout: Query execution timeout in seconds
            max_rows: Maximum number of rows to return
        """
        super().__init__(dsn, timeout, max_rows)
        self.database_name: Optional[str] = None

    def connect(self) -> None:
        """Establish MySQL connection.
        
        Raises:
            ConnectionError: If connection fails
        """
        from consult7.database.connection import parse_dsn

        timer = QueryTimer()
        error_msg = None

        try:
            with timer:
                dsn_parts = parse_dsn(self.dsn)
                database = dsn_parts.get("database")
                self.database_name = database if database else "no_database"

                # Connect to MySQL (with or without database selection)
                connection_params = {
                    "host": dsn_parts["host"],
                    "port": dsn_parts.get("port", 3306),
                    "user": dsn_parts["username"],
                    "password": dsn_parts["password"],
                    "connect_timeout": int(self.timeout),
                    "read_timeout": int(self.timeout),
                    "write_timeout": int(self.timeout),
                    "charset": 'utf8mb4',
                    "cursorclass": pymysql.cursors.DictCursor,
                }
                
                # Only add database parameter if specified in DSN
                if database:
                    connection_params["database"] = database
                
                self.connection = pymysql.connect(**connection_params)

            log_connection(self.dsn, success=True, duration=timer.duration)

        except Exception as e:
            error_msg = str(e)
            log_connection(self.dsn, success=False, error=error_msg, duration=timer.duration)
            raise ConnectionError(
                f"Failed to connect to MySQL database\n"
                f"  Error: {error_msg}\n"
                f"  Hint: Check that MySQL server is running and credentials are correct\n"
                f"  DSN format: mysql://user:password@host:port/database"
            ) from e

    def validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """Validate that query is read-only.
        
        Args:
            query: SQL query to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        return validate_query(query)

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute read-only query with timeout enforcement.
        
        Args:
            query: SQL query to execute
        
        Returns:
            List of result rows (each row is a dictionary)
        
        Raises:
            TimeoutError: If query exceeds timeout
            ValueError: If query is not read-only
            RuntimeError: If query execution fails
        """
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

        # Validate query is read-only
        is_valid, error_msg = self.validate_query(query)
        if not is_valid:
            log_query_execution(
                query=query,
                dsn=self.dsn,
                success=False,
                error=error_msg,
                blocked=True
            )
            raise ValueError(error_msg)

        timer = QueryTimer()
        error_msg = None
        results = []

        try:
            with timer:
                # Set session to read-only (defense-in-depth)
                with self.connection.cursor() as cursor:
                    cursor.execute("SET SESSION TRANSACTION READ ONLY")

                    # Add LIMIT clause if not present and max_rows specified
                    modified_query = self._add_limit_clause(query)

                    # Execute query
                    cursor.execute(modified_query)
                    results = cursor.fetchall()

            log_query_execution(
                query=query,
                dsn=self.dsn,
                success=True,
                row_count=len(results),
                duration=timer.duration
            )

            return results

        except pymysql.Error as e:
            error_msg = str(e)
            log_query_execution(
                query=query,
                dsn=self.dsn,
                success=False,
                error=error_msg,
                duration=timer.duration
            )

            # Check if timeout
            if "timeout" in error_msg.lower() or timer.duration >= self.timeout:
                raise TimeoutError(
                    f"Query execution timeout ({self.timeout}s exceeded)\n"
                    f"  Query: {query[:100]}{'...' if len(query) > 100 else ''}\n"
                    f"  Hint: Simplify query or add WHERE clause to reduce execution time"
                ) from e

            raise RuntimeError(
                f"Query execution failed\n"
                f"  Error: {error_msg}\n"
                f"  Query: {query[:100]}{'...' if len(query) > 100 else ''}"
            ) from e

    def _add_limit_clause(self, query: str) -> str:
        """Add LIMIT clause to SELECT query if not present.
        
        Args:
            query: SQL query
        
        Returns:
            Modified query with LIMIT clause
        """
        # Simple check: if query has LIMIT already, don't modify
        if "LIMIT" in query.upper():
            return query

        # If query is SELECT and no LIMIT, add one
        query_upper = query.strip().upper()
        if query_upper.startswith("SELECT") and self.max_rows > 0:
            return f"{query.rstrip(';')} LIMIT {self.max_rows}"

        return query

    def format_result(self, results: list[dict[str, Any]], query: str) -> str:
        """Format MySQL query results for AI consumption.
        
        Args:
            results: Query results
            query: Original query
        
        Returns:
            Formatted string suitable for LLM input
        """
        return format_database_results(results, query, self.database_name or "unknown")

    def close(self) -> None:
        """Close MySQL connection."""
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass  # Ignore errors on close
            finally:
                self.connection = None
