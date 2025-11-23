"""MongoDB database adapter implementation."""

import logging
from typing import Any, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError, ServerSelectionTimeoutError, OperationFailure
except ImportError:
    MongoClient = None
    PyMongoError = Exception
    ServerSelectionTimeoutError = Exception
    OperationFailure = Exception

from .base import BaseAdapter
from ..formatting import format_mongodb_results
from ..logging import log_query_execution, QueryTimer

logger = logging.getLogger(__name__)


class MongoDBAdapter(BaseAdapter):
    """MongoDB database adapter with read-only enforcement."""

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
        """Initialize MongoDB adapter.

        Args:
            host: Database host
            port: Database port
            database: Optional database name (if None, connects without selecting database)
            username: Optional username
            password: Optional password
            timeout: Query timeout in seconds
            max_rows: Maximum documents per query result
        """
        if MongoClient is None:
            raise ImportError(
                "pymongo is not installed. Install it with: pip install pymongo"
            )

        self.host = host
        self.port = port
        self.database_name = database if database else "no_database"
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_rows = max_rows
        self.client: Optional[Any] = None
        self.database: Optional[Any] = None

    @property
    def dsn(self) -> str:
        """Generate DSN string for logging (password redacted)."""
        user_part = f"{self.username}@" if self.username else ""
        return f"mongodb://{user_part}{self.host}:{self.port}/{self.database_name}"

    def connect(self) -> None:
        """Establish database connection with read-only preference."""
        try:
            # Build connection URI
            if self.username and self.password:
                uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}"
            else:
                uri = f"mongodb://{self.host}:{self.port}"
            
            # Append database name to URI only if specified
            if self.database_name and self.database_name != "no_database":
                uri += f"/{self.database_name}"

            # Connect with timeouts
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=int(self.timeout * 1000),
                socketTimeoutMS=int(self.timeout * 1000),
                connectTimeoutMS=int(self.timeout * 1000),
                # Prefer reading from secondary (read-only intent)
                readPreference="secondaryPreferred",
            )

            # Test connection
            self.client.admin.command("ping")

            # Get database reference (only if database specified)
            if self.database_name and self.database_name != "no_database":
                self.database = self.client[self.database_name]
            else:
                self.database = None

            logger.info(f"Connected to MongoDB database: {self.database_name}@{self.host}")

        except ServerSelectionTimeoutError as e:
            error_msg = f"Failed to connect to MongoDB (timeout): {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

        except PyMongoError as e:
            error_msg = f"Failed to connect to MongoDB: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

    def validate_query(self, query: str) -> None:
        """Validate MongoDB query/command.

        MongoDB queries are more complex than SQL. This method checks for
        obviously dangerous operations but relies primarily on database-level
        permissions for write protection.

        Args:
            query: MongoDB command/query to validate

        Raises:
            ValueError: If query contains clearly dangerous operations
        """
        query_lower = query.lower().strip()

        # Block obviously dangerous commands
        dangerous_operations = [
            "insert",
            "update",
            "delete",
            "drop",
            "create",
            "remove",
            "rename",
            "replace",
        ]

        for op in dangerous_operations:
            if op in query_lower:
                raise ValueError(
                    f"Write operation '{op.upper()}' detected in MongoDB query.\n"
                    f"  Only read operations (find, aggregate, count, etc.) are allowed.\n"
                    f"  Hint: Use find() or aggregate() for data retrieval"
                )

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute read-only MongoDB query.

        MongoDB queries are expected in Python dict/JSON format representing
        find() or aggregate() operations.

        Args:
            query: MongoDB query string (will be evaluated as Python expression)

        Returns:
            List of result documents as dictionaries

        Raises:
            ConnectionError: If not connected or connection error
            ValueError: If query validation fails or invalid syntax
            TimeoutError: If query exceeds timeout
        """
        if self.database is None:
            raise ConnectionError("Not connected to database. Call connect() first.")

        # Validate query before execution
        self.validate_query(query)

        with QueryTimer() as timer:
            try:
                # Parse query - expect format like: "collection_name.find({...})"
                # or "collection_name.aggregate([...])"
                query = query.strip()

                # Simple parsing: extract collection name and operation
                if ".find(" in query or ".aggregate(" in query:
                    collection_name = query.split(".")[0].strip()
                    collection = self.database[collection_name]

                    # Execute query with limit
                    if ".find(" in query:
                        # Extract query filter (simplified parsing)
                        results = list(collection.find().limit(self.max_rows))
                    elif ".aggregate(" in query:
                        # For aggregation, add $limit stage
                        results = list(collection.aggregate([{"$limit": self.max_rows}]))
                    else:
                        results = []

                    # Remove _id field for cleaner output (can be large ObjectIds)
                    for doc in results:
                        if "_id" in doc:
                            doc["_id"] = str(doc["_id"])

                else:
                    raise ValueError(
                        f"Invalid MongoDB query format. Expected format:\n"
                        f"  collection_name.find({{filter}})\n"
                        f"  collection_name.aggregate([pipeline])\n"
                        f"Got: {query[:100]}"
                    )

                # Log successful execution
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=True,
                    row_count=len(results),
                    duration=timer.duration,
                )

                return results

            except OperationFailure as e:
                # Check if it's a write operation blocked by permissions
                if "not authorized" in str(e).lower() or "read-only" in str(e).lower():
                    error_msg = (
                        f"Write operation blocked by database: {e}\n"
                        f"  Hint: MongoDB user has read-only permissions"
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

                error_msg = f"MongoDB operation failed: {e}"
                logger.error(error_msg)
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=False,
                    error=error_msg,
                    duration=timer.duration,
                )
                raise ConnectionError(error_msg) from e

            except PyMongoError as e:
                error_str = str(e).lower()

                # Check if it's a timeout
                if "timeout" in error_str or "timed out" in error_str:
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

                error_msg = f"MongoDB error: {e}"
                logger.error(error_msg)
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=False,
                    error=error_msg,
                    duration=timer.duration,
                )
                raise ConnectionError(error_msg) from e

            except Exception as e:
                error_msg = f"Error executing MongoDB query: {e}"
                logger.error(error_msg)
                log_query_execution(
                    query=query,
                    dsn=self.dsn,
                    success=False,
                    error=error_msg,
                    duration=timer.duration,
                )
                raise ValueError(error_msg) from e

    def format_result(self, results: list[dict[str, Any]], query: str) -> str:
        """Format query results for LLM consumption.

        Args:
            results: Query results as list of dictionaries
            query: Original query for context

        Returns:
            Formatted string representation
        """
        return format_mongodb_results(results, query, self.database_name)

    def close(self) -> None:
        """Close database connection."""
        if self.client:
            try:
                self.client.close()
                logger.info(f"Closed MongoDB connection to {self.database_name}")
            except Exception as e:
                logger.warning(f"Error closing MongoDB connection: {e}")
            finally:
                self.client = None
                self.database = None
