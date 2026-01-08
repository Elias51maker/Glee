"""SQLite database connection and helpers."""

import sqlite3
from pathlib import Path

from .schema import SQLITE_SCHEMAS

# Default database filename
SQLITE_DB_NAME = "glee.db"


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


def get_sqlite_connection(project_path: Path | None = None) -> sqlite3.Connection:
    """Get a SQLite connection.

    Args:
        project_path: Project root path. If None, uses current directory.

    Returns:
        SQLite connection object.
    """
    db_path = get_sqlite_path(project_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))


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
