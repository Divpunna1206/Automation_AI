from datetime import datetime
import json

from fastapi import Depends

from app.core.settings import Settings, get_settings
from app.db.sqlite import get_connection
from app.models.resume import ResumeVersionListResponse, ResumeVersionRecord, ResumeVersionStatus


class ResumeVersionRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def create(
        self,
        resume_version_id: str,
        title: str,
        company: str,
        ats_score: int,
        matched_keywords: list[str],
        missing_keywords: list[str],
        file_path: str | None,
        file_path_docx: str | None = None,
        job_queue_id: int | None = None,
        application_id: int | None = None,
    ) -> ResumeVersionRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        with get_connection(self.database_url) as connection:
            cursor = connection.execute(
                """
                INSERT INTO resume_versions (
                    resume_version_id, job_queue_id, application_id, title, company,
                    ats_score, matched_keywords, missing_keywords, file_path, file_path_docx, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resume_version_id,
                    job_queue_id,
                    application_id,
                    title,
                    company,
                    ats_score,
                    json.dumps(matched_keywords),
                    json.dumps(missing_keywords),
                    file_path,
                    file_path_docx,
                    ResumeVersionStatus.DRAFT.value,
                    now,
                ),
            )
            row = connection.execute("SELECT * FROM resume_versions WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_record(row)

    def list_versions(self, limit: int = 100) -> ResumeVersionListResponse:
        with get_connection(self.database_url) as connection:
            rows = connection.execute(
                "SELECT * FROM resume_versions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return ResumeVersionListResponse(versions=[self._to_record(row) for row in rows])

    def get(self, version_id: int) -> ResumeVersionRecord:
        with get_connection(self.database_url) as connection:
            row = connection.execute("SELECT * FROM resume_versions WHERE id = ?", (version_id,)).fetchone()
        if row is None:
            raise ValueError(f"Resume version {version_id} not found")
        return self._to_record(row)

    def update_status(self, version_id: int, status: ResumeVersionStatus) -> ResumeVersionRecord:
        if status == ResumeVersionStatus.SELECTED:
            return self.select(version_id)
        with get_connection(self.database_url) as connection:
            connection.execute("UPDATE resume_versions SET status = ? WHERE id = ?", (status.value, version_id))
            row = connection.execute("SELECT * FROM resume_versions WHERE id = ?", (version_id,)).fetchone()
        if row is None:
            raise ValueError(f"Resume version {version_id} not found")
        return self._to_record(row)

    def select(self, version_id: int) -> ResumeVersionRecord:
        with get_connection(self.database_url) as connection:
            row = connection.execute("SELECT * FROM resume_versions WHERE id = ?", (version_id,)).fetchone()
            if row is None:
                raise ValueError(f"Resume version {version_id} not found")
            if row["job_queue_id"] is not None:
                connection.execute(
                    "UPDATE resume_versions SET status = ? WHERE job_queue_id = ? AND id != ?",
                    (ResumeVersionStatus.REVIEWED.value, row["job_queue_id"], version_id),
                )
            if row["application_id"] is not None:
                connection.execute(
                    "UPDATE resume_versions SET status = ? WHERE application_id = ? AND id != ?",
                    (ResumeVersionStatus.REVIEWED.value, row["application_id"], version_id),
                )
            connection.execute(
                "UPDATE resume_versions SET status = ? WHERE id = ?",
                (ResumeVersionStatus.SELECTED.value, version_id),
            )
            selected = connection.execute("SELECT * FROM resume_versions WHERE id = ?", (version_id,)).fetchone()
        return self._to_record(selected)

    def archive(self, version_id: int) -> ResumeVersionRecord:
        return self.update_status(version_id, ResumeVersionStatus.ARCHIVED)

    def _to_record(self, row) -> ResumeVersionRecord:
        data = dict(row)
        data["matched_keywords"] = json.loads(data["matched_keywords"] or "[]")
        data["missing_keywords"] = json.loads(data["missing_keywords"] or "[]")
        return ResumeVersionRecord.model_validate(data)


def get_resume_version_repository(settings: Settings = Depends(get_settings)) -> ResumeVersionRepository:
    return ResumeVersionRepository(settings.database_url)
