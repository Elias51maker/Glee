"""Logging configuration for Glee with SQLite storage."""


import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loguru import logger

from glee.db.sqlite import get_sqlite_connection, init_sqlite

if TYPE_CHECKING:
    from loguru import Logger


class AgentRunLogger:
    """Logger for agent invocations - stores prompts, outputs, raw responses."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        if self._conn is None:
            self._conn = get_sqlite_connection(self.project_path)
        return self._conn

    def _init_db(self) -> None:
        """Initialize the agent_logs table using centralized schema."""
        init_sqlite(self.conn, tables=["agent_logs"])

    def log(
        self,
        agent: str,
        prompt: str,
        output: str | None = None,
        raw: str | None = None,
        error: str | None = None,
        exit_code: int = 0,
        duration_ms: int | None = None,
    ) -> str:
        """Log an agent run.

        Args:
            agent: Agent name (claude, codex, gemini).
            prompt: The prompt sent to the agent.
            output: Parsed/final output.
            raw: Raw output from subprocess (for debugging).
            error: Error message if failed.
            exit_code: Process exit code.
            duration_ms: Execution time in milliseconds.

        Returns:
            The log ID.
        """
        log_id = str(uuid4())[:8]
        self.conn.execute(
            """
            INSERT INTO agent_logs
            (id, timestamp, agent, prompt, output, raw, error, exit_code, duration_ms, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                log_id,
                datetime.now().isoformat(),
                agent,
                prompt,
                output,
                raw,
                error,
                exit_code,
                duration_ms,
                1 if exit_code == 0 and error is None else 0,
            ],
        )
        self.conn.commit()
        return log_id

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


_agent_logger: AgentRunLogger | None = None


def get_agent_logger(project_path: Path | None = None) -> AgentRunLogger | None:
    """Get or create the agent run logger.

    Args:
        project_path: Project path for .glee directory.

    Returns:
        AgentRunLogger instance or None if no project path.
    """
    global _agent_logger

    if _agent_logger is not None:
        return _agent_logger

    if project_path:
        _agent_logger = AgentRunLogger(project_path)
        return _agent_logger

    return None


def query_agent_logs(
    project_path: Path,
    agent: str | None = None,
    success_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query agent logs from SQLite.

    Args:
        project_path: Project path containing .glee directory.
        agent: Filter by agent name.
        success_only: Only return successful runs.
        limit: Max number of results.

    Returns:
        List of agent log records.
    """
    conn = get_sqlite_connection(project_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM agent_logs WHERE 1=1"
    params: list[Any] = []

    if agent:
        query += " AND agent = ?"
        params.append(agent)

    if success_only:
        query += " AND success = 1"

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        results = []
    finally:
        conn.close()

    return results


def get_agent_log(project_path: Path, log_id: str) -> dict[str, Any] | None:
    """Get a specific agent log entry.

    Args:
        project_path: Project path containing .glee directory.
        log_id: The log ID to fetch.

    Returns:
        Log record or None if not found.
    """
    conn = get_sqlite_connection(project_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute("SELECT * FROM agent_logs WHERE id = ?", [log_id])
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()

    return dict(row) if row else None


class SQLiteLogHandler:
    """Custom log handler that stores logs in SQLite."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        if self._conn is None:
            self._conn = get_sqlite_connection(self.project_path)
        return self._conn

    def _init_db(self) -> None:
        """Initialize the logs table using centralized schema."""
        init_sqlite(self.conn, tables=["logs"])

    def write(self, message: Any) -> None:
        """Write a log record to SQLite."""
        import json

        record = message.record
        _extra_json = json.dumps(record["extra"]) if record["extra"] else None  # Reserved for future use

        self.conn.execute(
            """
            INSERT INTO logs (timestamp, level, message)
            VALUES (?, ?, ?)
            """,
            [
                record["time"].isoformat(),
                record["level"].name,
                record["message"],
            ],
        )
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


_log_handler: SQLiteLogHandler | None = None


def setup_logging(project_path: Path | None = None) -> "Logger":
    """Configure loguru logging with SQLite storage.

    Args:
        project_path: Project path for .glee directory. If None, only console logging.

    Returns:
        Configured logger instance.
    """
    global _log_handler

    logger.remove()

    # Console logging
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG",
    )

    # SQLite logging if project path provided
    if project_path:
        _log_handler = SQLiteLogHandler(project_path)
        logger.add(_log_handler.write, level="DEBUG")

    return logger


def query_logs(
    project_path: Path,
    level: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query logs from SQLite.

    Args:
        project_path: Project path containing .glee directory.
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR).
        since: Filter logs after this time.
        until: Filter logs before this time.
        search: Search in message text.
        limit: Max number of results.

    Returns:
        List of log records.
    """
    conn = get_sqlite_connection(project_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM logs WHERE 1=1"
    params: list[Any] = []

    if level:
        query += " AND level = ?"
        params.append(level.upper())

    if since:
        query += " AND timestamp >= ?"
        params.append(since.isoformat())

    if until:
        query += " AND timestamp <= ?"
        params.append(until.isoformat())

    if search:
        query += " AND message LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        results = []
    finally:
        conn.close()

    return results


def get_log_stats(project_path: Path) -> dict[str, Any]:
    """Get log statistics.

    Args:
        project_path: Project path containing .glee directory.

    Returns:
        Dictionary with log stats.
    """
    conn = get_sqlite_connection(project_path)

    try:
        # Total count
        total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]

        # Count by level
        cursor = conn.execute(
            "SELECT level, COUNT(*) as count FROM logs GROUP BY level"
        )
        by_level = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        total = 0
        by_level = {}
    finally:
        conn.close()

    return {"total": total, "by_level": by_level}
