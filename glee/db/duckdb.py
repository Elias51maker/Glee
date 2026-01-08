"""DuckDB database connection and helpers."""

from pathlib import Path

import duckdb

from .schema import DUCKDB_SCHEMAS

# Default database filename
DUCKDB_DB_NAME = "memory.duckdb"


def get_duckdb_path(project_path: Path | None = None) -> Path:
    """Get the DuckDB database path.

    Args:
        project_path: Project root path. If None, uses current directory.

    Returns:
        Path to the DuckDB database file.
    """
    if project_path is None:
        project_path = Path.cwd()
    return project_path / ".glee" / DUCKDB_DB_NAME


def get_duckdb_connection(project_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection.

    Args:
        project_path: Project root path. If None, uses current directory.

    Returns:
        DuckDB connection object.
    """
    db_path = get_duckdb_path(project_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def init_duckdb(
    conn: duckdb.DuckDBPyConnection,
    tables: list[str] | None = None,
) -> None:
    """Initialize DuckDB tables.

    Args:
        conn: DuckDB connection.
        tables: List of table names to create. If None, creates all tables.
    """
    if tables is None:
        tables = list(DUCKDB_SCHEMAS.keys())

    for table_name in tables:
        if table_name not in DUCKDB_SCHEMAS:
            continue

        schema = DUCKDB_SCHEMAS[table_name]
        conn.execute(schema["table"])

        for index_sql in schema.get("indexes", []):
            conn.execute(index_sql)


def init_all_duckdb_tables(project_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Initialize all DuckDB tables and return connection.

    Args:
        project_path: Project root path. If None, uses current directory.

    Returns:
        DuckDB connection with all tables initialized.
    """
    conn = get_duckdb_connection(project_path)
    init_duckdb(conn)
    return conn
