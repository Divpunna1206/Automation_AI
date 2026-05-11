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
                canonical_job_url TEXT,
                dedupe_key TEXT,
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
        _add_column_if_missing(connection, "applications", "canonical_job_url", "TEXT")
        _add_column_if_missing(connection, "applications", "dedupe_key", "TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_applications_canonical_job_url ON applications(canonical_job_url) WHERE canonical_job_url IS NOT NULL"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_applications_dedupe_key ON applications(dedupe_key) WHERE dedupe_key IS NOT NULL"
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS discovered_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                job_url TEXT,
                canonical_url TEXT,
                dedupe_key TEXT,
                source TEXT NOT NULL DEFAULT 'manual',
                location TEXT,
                work_mode TEXT,
                description TEXT NOT NULL,
                required_skills TEXT NOT NULL DEFAULT '[]',
                fit_score INTEGER,
                recommendation TEXT,
                queue_status TEXT NOT NULL DEFAULT 'discovered',
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _add_column_if_missing(connection, "discovered_jobs", "canonical_url", "TEXT")
        _add_column_if_missing(connection, "discovered_jobs", "dedupe_key", "TEXT")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_discovered_jobs_status ON discovered_jobs(queue_status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_discovered_jobs_discovered_at ON discovered_jobs(discovered_at)"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_discovered_jobs_canonical_url ON discovered_jobs(canonical_url) WHERE canonical_url IS NOT NULL"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_discovered_jobs_dedupe_key ON discovered_jobs(dedupe_key) WHERE dedupe_key IS NOT NULL"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS resume_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_version_id TEXT NOT NULL UNIQUE,
                job_queue_id INTEGER,
                application_id INTEGER,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                ats_score INTEGER NOT NULL,
                matched_keywords TEXT NOT NULL DEFAULT '[]',
                missing_keywords TEXT NOT NULL DEFAULT '[]',
                file_path TEXT,
                file_path_docx TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _add_column_if_missing(connection, "resume_versions", "file_path_docx", "TEXT")
        _add_column_if_missing(connection, "resume_versions", "status", "TEXT NOT NULL DEFAULT 'draft'")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_resume_versions_job_queue_id ON resume_versions(job_queue_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_resume_versions_application_id ON resume_versions(application_id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS apply_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_queue_id INTEGER,
                application_id INTEGER,
                job_url TEXT NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                resume_version_id INTEGER,
                resume_file_path TEXT,
                cover_letter_text TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                fill_summary TEXT,
                field_results TEXT NOT NULL DEFAULT '[]',
                screenshot_paths TEXT NOT NULL DEFAULT '[]',
                errors TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_apply_sessions_status ON apply_sessions(status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_apply_sessions_job_queue_id ON apply_sessions(job_queue_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_apply_sessions_application_id ON apply_sessions(application_id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS apply_session_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apply_session_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                detected_field_label TEXT,
                answer_text TEXT,
                confidence_score REAL NOT NULL DEFAULT 0,
                answer_source TEXT NOT NULL,
                requires_manual_review INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_apply_session_questions_session_id ON apply_session_questions(apply_session_id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outreach_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                name TEXT,
                title TEXT,
                linkedin_url TEXT,
                email TEXT,
                source TEXT NOT NULL DEFAULT 'manual',
                confidence_score REAL NOT NULL DEFAULT 0.7,
                notes TEXT,
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_outreach_contacts_company ON outreach_contacts(company)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outreach_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_queue_id INTEGER,
                application_id INTEGER,
                apply_session_id INTEGER,
                contact_id INTEGER,
                channel TEXT NOT NULL,
                message_type TEXT NOT NULL DEFAULT 'initial',
                message_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'drafted',
                follow_up_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_outreach_records_status ON outreach_records(status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_outreach_records_follow_up_date ON outreach_records(follow_up_date)"
        )


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, declaration: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
