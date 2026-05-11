from datetime import datetime
import json

from fastapi import Depends

from app.core.settings import Settings, get_settings
from app.db.sqlite import get_connection
from app.models.apply_session import ApplySessionListResponse, ApplySessionRecord, ApplySessionStatus, FieldResult


class ApplySessionRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def create(
        self,
        job_url: str,
        company: str,
        title: str,
        job_queue_id: int | None = None,
        application_id: int | None = None,
        resume_version_id: int | None = None,
        resume_file_path: str | None = None,
        cover_letter_text: str | None = None,
        fill_summary: str | None = None,
        field_results: list[FieldResult] | None = None,
        errors: list[str] | None = None,
    ) -> ApplySessionRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        with get_connection(self.database_url) as connection:
            cursor = connection.execute(
                """
                INSERT INTO apply_sessions (
                    job_queue_id, application_id, job_url, company, title,
                    resume_version_id, resume_file_path, cover_letter_text, status,
                    fill_summary, field_results, screenshot_paths, errors, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_queue_id,
                    application_id,
                    job_url,
                    company,
                    title,
                    resume_version_id,
                    resume_file_path,
                    cover_letter_text,
                    ApplySessionStatus.PLANNED.value,
                    fill_summary,
                    json.dumps([item.model_dump() for item in field_results or []]),
                    "[]",
                    json.dumps(errors or []),
                    now,
                    now,
                ),
            )
            row = connection.execute("SELECT * FROM apply_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_record(row)

    def list_sessions(self, limit: int = 100) -> ApplySessionListResponse:
        with get_connection(self.database_url) as connection:
            rows = connection.execute(
                "SELECT * FROM apply_sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return ApplySessionListResponse(sessions=[self._to_record(row) for row in rows])

    def get(self, session_id: int) -> ApplySessionRecord:
        with get_connection(self.database_url) as connection:
            row = connection.execute("SELECT * FROM apply_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise ValueError(f"Apply session {session_id} not found")
        return self._to_record(row)

    def update(
        self,
        session_id: int,
        status: ApplySessionStatus | None = None,
        fill_summary: str | None = None,
        field_results: list[FieldResult] | None = None,
        screenshot_paths: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> ApplySessionRecord:
        current = self.get(session_id)
        values = {
            "id": session_id,
            "status": status.value if status else current.status.value,
            "fill_summary": fill_summary if fill_summary is not None else current.fill_summary,
            "field_results": json.dumps([item.model_dump() for item in (field_results if field_results is not None else current.field_results)]),
            "screenshot_paths": json.dumps(screenshot_paths if screenshot_paths is not None else current.screenshot_paths),
            "errors": json.dumps(errors if errors is not None else current.errors),
            "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
        }
        with get_connection(self.database_url) as connection:
            connection.execute(
                """
                UPDATE apply_sessions
                SET status = :status,
                    fill_summary = :fill_summary,
                    field_results = :field_results,
                    screenshot_paths = :screenshot_paths,
                    errors = :errors,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                values,
            )
            row = connection.execute("SELECT * FROM apply_sessions WHERE id = ?", (session_id,)).fetchone()
        return self._to_record(row)

    def _to_record(self, row) -> ApplySessionRecord:
        data = dict(row)
        data["field_results"] = json.loads(data["field_results"] or "[]")
        data["screenshot_paths"] = json.loads(data["screenshot_paths"] or "[]")
        data["errors"] = json.loads(data["errors"] or "[]")
        return ApplySessionRecord.model_validate(data)


def get_apply_session_repository(settings: Settings = Depends(get_settings)) -> ApplySessionRepository:
    return ApplySessionRepository(settings.database_url)
