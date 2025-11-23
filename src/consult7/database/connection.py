"""Database connection management and DSN parsing."""

import queue
import threading
from typing import Any
from urllib.parse import urlparse


def parse_dsn(dsn: str) -> dict:
    """Parse database connection string (DSN) into components.
    
    Args:
        dsn: Database connection string in format:
             protocol://user:password@host:port/database
             Examples:
             - mysql://user:pass@localhost:3306/mydb
             - postgresql://user:pass@localhost:5432/mydb
             - sqlite:///path/to/database.db
             - mongodb://user:pass@localhost:27017/mydb
    
    Returns:
        Dictionary with keys: protocol, username, password, host, port, database
    
    Raises:
        ValueError: If DSN format is invalid
    """
    parsed = urlparse(dsn)

    if not parsed.scheme:
        raise ValueError(
            "Invalid DSN format: missing protocol\n"
            "  Hint: Use format protocol://user:pass@host:port/database\n"
            "  Examples:\n"
            "    - mysql://user:pass@localhost:3306/mydb\n"
            "    - postgresql://user:pass@localhost:5432/mydb\n"
            "    - sqlite:///path/to/database.db\n"
            "    - mongodb://user:pass@localhost:27017/mydb"
        )

    # Extract database name from path
    database = parsed.path.lstrip("/") if parsed.path else None

    return {
        "protocol": parsed.scheme,
        "username": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port,
        "database": database,
    }


class ConnectionPool:
    """Queue-based connection pool for database connections.
    
    Manages a pool of database connections per DSN, allowing connection reuse
    and preventing connection exhaustion.
    
    Thread-safe implementation using queue.Queue for connection management.
    """

    # Class-level dictionary to store pools per DSN
    _pools: dict[str, "ConnectionPool"] = {}
    _lock = threading.Lock()

    def __init__(self, dsn: str, pool_size: int = 5):
        """Initialize connection pool.
        
        Args:
            dsn: Database connection string
            pool_size: Maximum number of connections in pool
        """
        self.dsn = dsn
        self.pool_size = pool_size
        self._pool: queue.Queue[Any] = queue.Queue(maxsize=pool_size)
        self._connection_count = 0
        self._count_lock = threading.Lock()

    @classmethod
    def get_pool(cls, dsn: str, pool_size: int = 5) -> "ConnectionPool":
        """Get or create connection pool for DSN.
        
        Args:
            dsn: Database connection string
            pool_size: Maximum number of connections in pool
        
        Returns:
            ConnectionPool instance for the DSN
        """
        with cls._lock:
            if dsn not in cls._pools:
                cls._pools[dsn] = ConnectionPool(dsn, pool_size)
            return cls._pools[dsn]

    def acquire(self, adapter_factory, timeout: float = 30.0) -> Any:
        """Acquire connection from pool or create new one.
        
        Args:
            adapter_factory: Callable that creates new adapter instance
            timeout: Maximum time to wait for connection
        
        Returns:
            Database adapter instance
        
        Raises:
            queue.Empty: If no connection available within timeout
        """
        try:
            # Try to get existing connection from pool
            connection = self._pool.get(block=True, timeout=timeout)
            return connection
        except queue.Empty:
            # No available connection in pool
            with self._count_lock:
                if self._connection_count < self.pool_size:
                    # Create new connection if under limit
                    self._connection_count += 1
                    connection = adapter_factory()
                    connection.connect()
                    return connection
                else:
                    # Pool exhausted, wait for connection
                    raise queue.Empty(
                        f"Connection pool exhausted for {self.dsn}. "
                        f"Maximum pool size: {self.pool_size}"
                    )

    def release(self, connection: Any) -> None:
        """Release connection back to pool.
        
        Args:
            connection: Database adapter instance to return to pool
        """
        try:
            self._pool.put(connection, block=False)
        except queue.Full:
            # Pool is full, close the connection
            connection.close()
            with self._count_lock:
                self._connection_count -= 1

    def close_all(self) -> None:
        """Close all connections in pool."""
        while not self._pool.empty():
            try:
                connection = self._pool.get(block=False)
                connection.close()
            except queue.Empty:
                break

        with self._count_lock:
            self._connection_count = 0
