"""Database management for Glee."""

from .duckdb import get_duckdb_connection, init_duckdb
from .schema import DUCKDB_SCHEMAS, SQLITE_SCHEMAS
from .sqlite import get_sqlite_connection, init_sqlite

__all__ = [
    "SQLITE_SCHEMAS",
    "DUCKDB_SCHEMAS",
    "get_sqlite_connection",
    "get_duckdb_connection",
    "init_sqlite",
    "init_duckdb",
]
