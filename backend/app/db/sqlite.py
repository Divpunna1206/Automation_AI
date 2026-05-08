import sqlite3
from pathlib import Path

from app.models.application import ApplicationStatus


def _path_from_database_url(database_url: str) -> Path:
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Phase 1 supports sqlite:/// URLs. Repository boundary is ready for PostgreSQL later.")
    return Path(database_url.replace("sqlite:///", "", 1))


def get_connection(database_url: str) -> sqlite3.Connection:
    db_path = _path_from_database_url(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_url: str) -> None:
    with get_connection(database_url) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                job_url TEXT,
                source TEXT NOT NULL DEFAULT 'manual',
                fit_score INTEGER,
                recommendation TEXT,
                resume_version TEXT,
                resume_markdown TEXT,
                resume_pdf_path TEXT,
                cover_letter TEXT,
                status TEXT NOT NULL DEFAULT 'discovered',
                follow_up_date TEXT,
                notes TEXT,
                discovered_at TEXT,
                reviewed_at TEXT,
                materials_generated_at TEXT,
                approved_at TEXT,
                form_prepared_at TEXT,
                submitted_at TEXT,
                interview_at TEXT,
                rejected_at TEXT,
                offer_at TEXT,
                skipped_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_applications_follow_up_date ON applications(follow_up_date)"
        )
        connection.execute(
            "UPDATE applications SET status = ? WHERE status = 'draft'",
            (ApplicationStatus.DISCOVERED.value,),
        )
        _add_column_if_missing(connection, "applications", "resume_pdf_path", "TEXT")
        _add_column_if_missing(connection, "applications", "discovered_at", "TEXT")
        _add_column_if_missing(connection, "applications", "reviewed_at", "TEXT")
        _add_column_if_missing(connection, "applications", "materials_generated_at", "TEXT")
        _add_column_if_missing(connection, "applications", "approved_at", "TEXT")
        _add_column_if_missing(connection, "applications", "form_prepared_at", "TEXT")
        _add_column_if_missing(connection, "applications", "submitted_at", "TEXT")
        _add_column_if_missing(connection, "applications", "interview_at", "TEXT")
        _add_column_if_missing(connection, "applications", "rejected_at", "TEXT")
        _add_column_if_missing(connection, "applications", "offer_at", "TEXT")
        _add_column_if_missing(connection, "applications", "skipped_at", "TEXT")


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, declaration: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
