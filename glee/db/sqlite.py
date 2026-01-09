"""SQLite database connection and helpers."""

import sqlite3
import threading
from pathlib import Path

from .schema import SQLITE_SCHEMAS

# Default database filename
SQLITE_DB_NAME = "glee.db"

# Thread-local storage for SQLite connections
_thread_local = threading.local()


def get_sqlite_path(project_path: Path | None = None) -> Path:
    """Get the SQLite database path.

    Args:
        project_path: Project root path. If None, uses current directory.

    Returns:
        Path to the SQLite database file.
    """
    if project_path is None:
        project_path = Path.cwd()
    return project_path / ".glee" / SQLITE_DB_NAME


def _get_connection_cache() -> dict[str, sqlite3.Connection]:
    """Get the thread-local connection cache, creating if needed."""
    if not hasattr(_thread_local, "connections"):
        _thread_local.connections = {}
    # Thread-local attributes are dynamically typed, cast to expected type
    cache: dict[str, sqlite3.Connection] = _thread_local.connections  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    return cache


def get_sqlite_connection(project_path: Path | None = None) -> sqlite3.Connection:
    """Get a thread-local SQLite connection.

    Each thread gets its own connection to prevent "database is locked" errors
    when multiple threads (e.g., parallel MCP reviews) write concurrently.

    Args:
        project_path: Project root path. If None, uses current directory.

    Returns:
        SQLite connection object (thread-local).
    """
    db_path = get_sqlite_path(project_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_key = str(db_path)

    connections = _get_connection_cache()

    # Check if we have a valid connection for this path in this thread
    if db_key in connections:
        conn = connections[db_key]
        try:
            # Test if connection is still valid
            conn.execute("SELECT 1")
            return conn
        except sqlite3.ProgrammingError:
            # Connection was closed, remove from cache
            del connections[db_key]

    # Create new connection for this thread
    conn = sqlite3.connect(str(db_path))
    connections[db_key] = conn
    return conn


def close_thread_connections() -> None:
    """Close all SQLite connections for the current thread.

    Call this when a thread is finishing to clean up resources.
    """
    if hasattr(_thread_local, "connections"):
        connections = _get_connection_cache()
        for conn in connections.values():
            try:
                conn.close()
            except Exception:
                pass
        connections.clear()


def init_sqlite(
    conn: sqlite3.Connection,
    tables: list[str] | None = None,
) -> None:
    """Initialize SQLite tables.

    Args:
        conn: SQLite connection.
        tables: List of table names to create. If None, creates all tables.
    """
    if tables is None:
        tables = list(SQLITE_SCHEMAS.keys())

    for table_name in tables:
        if table_name not in SQLITE_SCHEMAS:
            continue

        schema = SQLITE_SCHEMAS[table_name]
        conn.execute(schema["table"])

        for index_sql in schema.get("indexes", []):
            conn.execute(index_sql)

    conn.commit()


def init_all_sqlite_tables(project_path: Path | None = None) -> sqlite3.Connection:
    """Initialize all SQLite tables and return connection.

    Args:
        project_path: Project root path. If None, uses current directory.

    Returns:
        SQLite connection with all tables initialized.
    """
    conn = get_sqlite_connection(project_path)
    init_sqlite(conn)
    return conn
