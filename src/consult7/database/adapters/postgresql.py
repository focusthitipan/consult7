"""PostgreSQL database adapter implementation."""

import logging
from typing import Any, Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

from .base import BaseAdapter
from ..validation import validate_query
from ..formatting import format_database_results
from ..logging import log_query_execution, QueryTimer

logger = logging.getLogger(__name__)


class PostgreSQLAdapter(BaseAdapter):
    """PostgreSQL database adapter with read-only enforcement."""

    def __init__(
        self,
        host: str,
        port: int,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 30.0,
        max_rows: int = 10_000,
    ):
        """Initialize PostgreSQL adapter.

        Args:
            host: Database host
            port: Database port
            database: Optional database name (if None, connects without selecting database)
            username: Optional username
            password: Optional password
            timeout: Query timeout in seconds
            max_rows: Maximum rows per query result
        """
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is not installed. Install it with: pip install psycopg2-binary"
            )

        self.host = host
        self.port = port
        self.database = database if database else "no_database"
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_rows = max_rows
        self.connection: Optional[Any] = None

    @property
    def dsn(self) -> str:
        """Generate DSN string for logging (password redacted)."""
        user_part = f"{self.username}@" if self.username else ""
        return f"postgresql://{user_part}{self.host}:{self.port}/{self.database}"

    def connect(self) -> None:
        """Establish database connection with read-only mode."""
        try:
            # Build connection parameters
            conn_params = {
                "host": self.host,
                "port": self.port,
                "connect_timeout": int(self.timeout),
                "options": f"-c statement_timeout={int(self.timeout * 1000)}",  # milliseconds
            }

            # Only add database if specified (not None)
            if self.database and self.database != "no_database":
                conn_params["database"] = self.database

            if self.username:
                conn_params["user"] = self.username
            if self.password:
                conn_params["password"] = self.password

            self.connection = psycopg2.connect(**conn_params)

            # Enforce read-only mode at session level
            cursor = self.connection.cursor()
            cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
            cursor.close()

            logger.info(f"Connected to PostgreSQL database: {self.database}@{self.host}")

        except psycopg2.Error as e:
            error_msg = f"Failed to connect to PostgreSQL: {e}"
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
                # Execute with dict cursor for named columns
                cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Auto-inject LIMIT if not present and max_rows > 0
                query_upper = query.upper().strip()
                if self.max_rows > 0 and "LIMIT" not in query_upper:
                    # Check if this is a SELECT query
                    if query_upper.startswith("SELECT"):
                        query = f"{query.rstrip(';')} LIMIT {self.max_rows}"
                        logger.debug(f"Auto-injected LIMIT {self.max_rows}")

                cursor.execute(query)
                results = cursor.fetchall()
                cursor.close()

                # Convert RealDictRow to regular dict
                results = [dict(row) for row in results]

                # Log successful execution
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=True,
                    row_count=len(results),
                    duration=timer.duration,
                )

                return results

            except psycopg2.errors.QueryCanceled as e:
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

            except psycopg2.errors.InsufficientPrivilege as e:
                error_msg = (
                    f"Write operation blocked by database: {e}\n"
                    f"  Hint: PostgreSQL session is set to READ ONLY mode"
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

            except psycopg2.Error as e:
                error_msg = f"PostgreSQL error: {e}"
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
        return format_database_results(results, query, self.database)

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info(f"Closed PostgreSQL connection to {self.database}")
            except Exception as e:
                logger.warning(f"Error closing PostgreSQL connection: {e}")
            finally:
                self.connection = None
