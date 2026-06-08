"""Database connection and initialization for AFL tipping factory."""

import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "afl_tipping_factory.db"


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a sqlite3 connection with row factory."""
    path = Path(db_path) if db_path else DEFAULT_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    schema = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()
    conn.executescript(schema)
    conn.commit()
    return conn
