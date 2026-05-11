from datetime import datetime
import re
import sqlite3
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Depends

from app.core.settings import Settings, get_settings
from app.db.sqlite import get_connection
from app.models.application import (
    ApplicationListResponse,
    ApplicationRecord,
    ApplicationSaveRequest,
    ApplicationStatus,
    ApplicationStatusUpdateRequest,
    STATUS_ORDER,
)
from app.models.dashboard import DashboardStatsResponse


class ApplicationRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def save(self, payload: ApplicationSaveRequest) -> ApplicationRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        values = payload.model_dump()
        values["follow_up_date"] = values["follow_up_date"].isoformat() if values["follow_up_date"] else None
        values["status"] = self._normalize_status(values["status"])
        values["canonical_job_url"] = self._canonical_job_url(values["job_url"])
        values["dedupe_key"] = self._dedupe_key(
            company=values["company"],
            title=values["title"],
            source=values["source"],
            canonical_job_url=values["canonical_job_url"],
        )
        values.update(self._status_timestamp_values(values["status"], now))

        with get_connection(self.database_url) as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO applications (
                        company, title, job_url, canonical_job_url, dedupe_key, source,
                        fit_score, recommendation,
                        resume_version, resume_markdown, resume_pdf_path, cover_letter, status,
                        follow_up_date, notes,
                        discovered_at, reviewed_at, materials_generated_at, approved_at,
                        form_prepared_at, submitted_at, interview_at, rejected_at, offer_at, skipped_at,
                        created_at, updated_at
                    ) VALUES (
                        :company, :title, :job_url, :canonical_job_url, :dedupe_key, :source,
                        :fit_score, :recommendation,
                        :resume_version, :resume_markdown, :resume_pdf_path, :cover_letter, :status,
                        :follow_up_date, :notes,
                        :discovered_at, :reviewed_at, :materials_generated_at, :approved_at,
                        :form_prepared_at, :submitted_at, :interview_at, :rejected_at, :offer_at, :skipped_at,
                        :created_at, :updated_at
                    )
                    """,
                    {**values, "created_at": now, "updated_at": now},
                )
                application_id = cursor.lastrowid
                row = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
            except sqlite3.IntegrityError:
                row = self._find_duplicate(connection, values["canonical_job_url"], values["dedupe_key"])
                if row is None:
                    raise
        return self._to_record(row)

    def list_applications(self, limit: int = 100) -> ApplicationListResponse:
        with get_connection(self.database_url) as connection:
            rows = connection.execute(
                "SELECT * FROM applications ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return ApplicationListResponse(applications=[self._to_record(row) for row in rows])

    def get(self, application_id: int) -> ApplicationRecord:
        with get_connection(self.database_url) as connection:
            row = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if row is None:
            raise ValueError(f"Application {application_id} not found")
        return self._to_record(row)

    def update_status(self, application_id: int, payload: ApplicationStatusUpdateRequest) -> ApplicationRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        normalized_status = self._normalize_status(payload.status)
        stage_updates = self._status_timestamp_values(normalized_status, now)
        with get_connection(self.database_url) as connection:
            connection.execute(
                """
                UPDATE applications
                SET status = :status,
                    follow_up_date = COALESCE(:follow_up_date, follow_up_date),
                    notes = COALESCE(:notes, notes),
                    discovered_at = COALESCE(:discovered_at, discovered_at),
                    reviewed_at = COALESCE(:reviewed_at, reviewed_at),
                    materials_generated_at = COALESCE(:materials_generated_at, materials_generated_at),
                    approved_at = COALESCE(:approved_at, approved_at),
                    form_prepared_at = COALESCE(:form_prepared_at, form_prepared_at),
                    submitted_at = COALESCE(:submitted_at, submitted_at),
                    interview_at = COALESCE(:interview_at, interview_at),
                    rejected_at = COALESCE(:rejected_at, rejected_at),
                    offer_at = COALESCE(:offer_at, offer_at),
                    skipped_at = COALESCE(:skipped_at, skipped_at),
                    updated_at = :updated_at
                WHERE id = :id
                """,
                {
                    "id": application_id,
                    "status": normalized_status,
                    "follow_up_date": payload.follow_up_date.isoformat() if payload.follow_up_date else None,
                    "notes": payload.notes,
                    "updated_at": now,
                    **stage_updates,
                },
            )
            row = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if row is None:
            raise ValueError(f"Application {application_id} not found")
        return self._to_record(row)

    def dashboard_stats(self) -> DashboardStatsResponse:
        with get_connection(self.database_url) as connection:
            counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_jobs,
                    SUM(CASE WHEN follow_up_date IS NOT NULL AND DATE(follow_up_date) <= DATE('now') THEN 1 ELSE 0 END) AS due_follow_ups,
                    AVG(fit_score) AS average_fit_score
                FROM applications
                """
            ).fetchone()
            status_rows = connection.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM applications
                GROUP BY status
                """
            ).fetchall()
            recent = connection.execute(
                "SELECT * FROM applications ORDER BY created_at DESC LIMIT 20"
            ).fetchall()

        status_counts = {status.value: 0 for status in STATUS_ORDER}
        for row in status_rows:
            status_counts[row["status"]] = row["count"]

        return DashboardStatsResponse(
            total_jobs=counts["total_jobs"] or 0,
            average_fit_score=round(counts["average_fit_score"], 1) if counts["average_fit_score"] is not None else None,
            due_follow_ups=counts["due_follow_ups"] or 0,
            status_counts=status_counts,
            recent_applications=[self._to_record(row) for row in recent],
        )

    def _to_record(self, row) -> ApplicationRecord:
        data = dict(row)
        return ApplicationRecord.model_validate(data)

    def _normalize_status(self, status: ApplicationStatus | str) -> str:
        value = status.value if isinstance(status, ApplicationStatus) else str(status)
        if value == "draft":
            return ApplicationStatus.DISCOVERED.value
        return value

    def _canonical_job_url(self, job_url: str | None) -> str | None:
        if not job_url:
            return None
        parsed = urlsplit(job_url.strip())
        if not parsed.scheme or not parsed.netloc:
            return self._normalize_token(job_url)
        query = urlencode(
            sorted(
                (key, value)
                for key, value in parse_qsl(parsed.query, keep_blank_values=False)
                if not key.lower().startswith("utm_")
            )
        )
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))

    def _dedupe_key(self, company: str, title: str, source: str, canonical_job_url: str | None) -> str:
        if canonical_job_url:
            return f"url:{canonical_job_url}"
        return "manual:" + "|".join(
            [
                self._normalize_token(company),
                self._normalize_token(title),
                self._normalize_token(source or "manual"),
            ]
        )

    def _normalize_token(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())

    def _find_duplicate(self, connection, canonical_job_url: str | None, dedupe_key: str):
        if canonical_job_url:
            row = connection.execute(
                "SELECT * FROM applications WHERE canonical_job_url = ?",
                (canonical_job_url,),
            ).fetchone()
            if row is not None:
                return row
        return connection.execute(
            "SELECT * FROM applications WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()

    def _status_timestamp_values(self, status: str, now: str) -> dict[str, str | None]:
        fields = {
            "discovered_at": None,
            "reviewed_at": None,
            "materials_generated_at": None,
            "approved_at": None,
            "form_prepared_at": None,
            "submitted_at": None,
            "interview_at": None,
            "rejected_at": None,
            "offer_at": None,
            "skipped_at": None,
        }
        timestamp_field = f"{status}_at"
        if timestamp_field in fields:
            fields[timestamp_field] = now
        if status != ApplicationStatus.DISCOVERED.value and fields["discovered_at"] is None:
            fields["discovered_at"] = now
        return fields


def get_application_repository(settings: Settings = Depends(get_settings)) -> ApplicationRepository:
    return ApplicationRepository(settings.database_url)
