"""SQLite database adapter implementation."""

import logging
import sqlite3
from typing import Any, Optional

from .base import BaseAdapter
from ..validation import validate_query
from ..formatting import format_database_results
from ..logging import log_query_execution, QueryTimer

logger = logging.getLogger(__name__)


class SQLiteAdapter(BaseAdapter):
    """SQLite database adapter with read-only enforcement."""

    def __init__(
        self,
        database_path: str,
        timeout: float = 30.0,
        max_rows: int = 10_000,
    ):
        """Initialize SQLite adapter.

        Args:
            database_path: Path to SQLite database file
            timeout: Query timeout in seconds
            max_rows: Maximum rows per query result
        """
        self.database_path = database_path
        self.timeout = timeout
        self.max_rows = max_rows
        self.connection: Optional[sqlite3.Connection] = None

    @property
    def dsn(self) -> str:
        """Generate DSN string for logging."""
        return f"sqlite:///{self.database_path}"

    def connect(self) -> None:
        """Establish database connection with read-only mode."""
        try:
            # Open in read-only mode using URI
            # Note: This requires Python 3.4+ and SQLite 3.4.0+
            uri = f"file:{self.database_path}?mode=ro"
            self.connection = sqlite3.connect(
                uri,
                timeout=self.timeout,
                uri=True,
                check_same_thread=False,  # Allow use across threads
            )

            # Enable dictionary cursor
            self.connection.row_factory = sqlite3.Row

            # Set additional timeouts for queries
            self.connection.execute(f"PRAGMA busy_timeout = {int(self.timeout * 1000)}")

            logger.info(f"Connected to SQLite database (read-only): {self.database_path}")

        except sqlite3.Error as e:
            error_msg = f"Failed to connect to SQLite: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

    def validate_query(self, query: str) -> None:
        """Validate query is read-only.

        Args:
            query: SQL query to validate

        Raises:
            ValueError: If query contains write operations
        """
        is_valid, error_message = validate_query(query)
        if not is_valid:
            raise ValueError(error_message)

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute read-only query with timeout and row limits.

        Args:
            query: SQL query to execute

        Returns:
            List of result rows as dictionaries

        Raises:
            ConnectionError: If not connected or connection error
            ValueError: If query validation fails
            TimeoutError: If query exceeds timeout
        """
        if not self.connection:
            raise ConnectionError("Not connected to database. Call connect() first.")

        # Validate query before execution
        self.validate_query(query)

        with QueryTimer() as timer:
            try:
                # Auto-inject LIMIT if not present and max_rows > 0
                query_upper = query.upper().strip()
                if self.max_rows > 0 and "LIMIT" not in query_upper:
                    # Check if this is a SELECT query
                    if query_upper.startswith("SELECT"):
                        query = f"{query.rstrip(';')} LIMIT {self.max_rows}"
                        logger.debug(f"Auto-injected LIMIT {self.max_rows}")

                cursor = self.connection.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                cursor.close()

                # Convert sqlite3.Row to dict
                results = [dict(row) for row in rows]

                # Log successful execution
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=True,
                    row_count=len(results),
                    duration=timer.duration,
                )

                return results

            except sqlite3.OperationalError as e:
                error_str = str(e).lower()

                # Check if it's a timeout
                if "timeout" in error_str or "locked" in error_str:
                    error_msg = f"Query exceeded timeout ({self.timeout}s): {e}"
                    logger.error(error_msg)
                    log_query_execution(
                        query=query,
                        dsn=self.dsn,
                        success=False,
                        error=error_msg,
                        duration=timer.duration,
                    )
                    raise TimeoutError(error_msg) from e

                # Check if it's a write attempt (read-only mode)
                if "readonly" in error_str or "attempt to write" in error_str:
                    error_msg = (
                        f"Write operation blocked by database: {e}\n"
                        f"  Hint: SQLite opened in read-only mode (URI parameter mode=ro)"
                    )
                    logger.warning(error_msg)
                    log_query_execution(
                        query=query,
                        dsn=self.dsn,
                        success=False,
                        error=error_msg,
                        duration=timer.duration,
                    )
                    raise ValueError(error_msg) from e

                # Other operational error
                error_msg = f"SQLite error: {e}"
                logger.error(error_msg)
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=False,
                    error=error_msg,
                    duration=timer.duration,
                )
                raise ConnectionError(error_msg) from e

            except sqlite3.Error as e:
                error_msg = f"SQLite error: {e}"
                logger.error(error_msg)
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=False,
                    error=error_msg,
                    duration=timer.duration,
                )
                raise ConnectionError(error_msg) from e

    def format_result(self, results: list[dict[str, Any]], query: str) -> str:
        """Format query results for LLM consumption.

        Args:
            results: Query results as list of dictionaries
            query: Original query for context

        Returns:
            Formatted string representation
        """
        return format_database_results(results, query, self.database_path)

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info(f"Closed SQLite connection to {self.database_path}")
            except Exception as e:
                logger.warning(f"Error closing SQLite connection: {e}")
            finally:
                self.connection = None
