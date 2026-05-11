from datetime import datetime
import json
import re
import sqlite3
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Depends

from app.core.settings import Settings, get_settings
from app.db.repository import ApplicationRepository
from app.db.sqlite import get_connection
from app.models.application import ApplicationSaveRequest, ApplicationStatus
from app.models.job_queue import (
    DailyTargetStatsResponse,
    DiscoveredJobListResponse,
    DiscoveredJobRecord,
    DiscoveredJobSaveRequest,
    DiscoveredJobSaveResult,
    JobQueueFilters,
    QueueStatus,
)


class DiscoveryQueueRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def save_discovered_job(self, payload: DiscoveredJobSaveRequest) -> DiscoveredJobSaveResult:
        now = datetime.utcnow().isoformat(timespec="seconds")
        values = payload.model_dump()
        canonical_url = self.canonical_url(values["job_url"])
        dedupe_key = self.dedupe_key(values["company"], values["title"], values["source"], canonical_url)
        values["canonical_url"] = canonical_url
        values["dedupe_key"] = dedupe_key
        values["required_skills"] = json.dumps(values["required_skills"])
        values["queue_status"] = self._normalize_status(values["queue_status"])

        with get_connection(self.database_url) as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO discovered_jobs (
                        title, company, job_url, canonical_url, dedupe_key, source,
                        location, work_mode, description, required_skills, fit_score,
                        recommendation, queue_status, discovered_at, updated_at
                    ) VALUES (
                        :title, :company, :job_url, :canonical_url, :dedupe_key, :source,
                        :location, :work_mode, :description, :required_skills, :fit_score,
                        :recommendation, :queue_status, :discovered_at, :updated_at
                    )
                    """,
                    {**values, "discovered_at": now, "updated_at": now},
                )
                row = connection.execute("SELECT * FROM discovered_jobs WHERE id = ?", (cursor.lastrowid,)).fetchone()
                return DiscoveredJobSaveResult(job=self._to_record(row), created=True)
            except sqlite3.IntegrityError:
                row = self._find_duplicate(connection, canonical_url, dedupe_key)
                if row is None:
                    raise
                row = self._merge_duplicate(connection, row, values, now)
                return DiscoveredJobSaveResult(job=self._to_record(row), created=False)

    def list_discovered_jobs(
        self,
        status: QueueStatus | None = None,
        limit: int = 100,
        filters: JobQueueFilters | None = None,
    ) -> DiscoveredJobListResponse:
        active_filters = filters or JobQueueFilters(status=status, limit=limit)
        clauses: list[str] = []
        params: list[object] = []
        if active_filters.status:
            clauses.append("queue_status = ?")
            params.append(active_filters.status.value)
        if active_filters.source:
            clauses.append("LOWER(source) = LOWER(?)")
            params.append(active_filters.source.strip())
        if active_filters.min_fit_score is not None:
            clauses.append("fit_score >= ?")
            params.append(active_filters.min_fit_score)
        if active_filters.location:
            clauses.append("LOWER(COALESCE(location, '')) LIKE ?")
            params.append(f"%{active_filters.location.strip().lower()}%")
        if active_filters.work_mode:
            clauses.append("LOWER(COALESCE(work_mode, '')) = LOWER(?)")
            params.append(active_filters.work_mode.strip())
        if active_filters.discovered_from:
            clauses.append("DATE(discovered_at) >= DATE(?)")
            params.append(active_filters.discovered_from.isoformat())
        if active_filters.discovered_to:
            clauses.append("DATE(discovered_at) <= DATE(?)")
            params.append(active_filters.discovered_to.isoformat())
        if active_filters.search:
            search = f"%{active_filters.search.strip().lower()}%"
            clauses.append(
                "(LOWER(title) LIKE ? OR LOWER(company) LIKE ? OR LOWER(description) LIKE ? OR LOWER(required_skills) LIKE ?)"
            )
            params.extend([search, search, search, search])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(active_filters.limit)
        with get_connection(self.database_url) as connection:
            rows = connection.execute(
                f"SELECT * FROM discovered_jobs {where} ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
        return DiscoveredJobListResponse(jobs=[self._to_record(row) for row in rows])

    def update_queue_status(self, job_id: int, status: QueueStatus) -> DiscoveredJobRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        with get_connection(self.database_url) as connection:
            connection.execute(
                """
                UPDATE discovered_jobs
                SET queue_status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, now, job_id),
            )
            row = connection.execute("SELECT * FROM discovered_jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"Discovered job {job_id} not found")
        return self._to_record(row)

    def shortlist_job(self, job_id: int) -> DiscoveredJobRecord:
        return self.update_queue_status(job_id, QueueStatus.SHORTLISTED)

    def skip_job(self, job_id: int) -> DiscoveredJobRecord:
        return self.update_queue_status(job_id, QueueStatus.SKIPPED)

    def convert_to_application(self, job_id: int, application_repository: ApplicationRepository) -> DiscoveredJobRecord:
        job = self.get(job_id)
        application_repository.save(
            ApplicationSaveRequest(
                company=job.company,
                title=job.title,
                job_url=job.job_url,
                source=job.source,
                fit_score=job.fit_score,
                recommendation=job.recommendation,
                status=ApplicationStatus.REVIEWED,
                notes="Converted from discovered jobs queue. Human approval still required before applying.",
            )
        )
        return self.update_queue_status(job_id, QueueStatus.APPLIED)

    def get_daily_target_stats(self, daily_target: int) -> DailyTargetStatsResponse:
        with get_connection(self.database_url) as connection:
            discovered_today = connection.execute(
                "SELECT COUNT(*) AS count FROM discovered_jobs WHERE DATE(discovered_at) = DATE('now')"
            ).fetchone()["count"]
            rows = connection.execute(
                """
                SELECT queue_status, COUNT(*) AS count
                FROM discovered_jobs
                WHERE DATE(updated_at) = DATE('now')
                GROUP BY queue_status
                """
            ).fetchall()
        counts = {status.value: 0 for status in QueueStatus}
        for row in rows:
            counts[row["queue_status"]] = row["count"]
        applied_today = counts[QueueStatus.APPLIED.value]
        return DailyTargetStatsResponse(
            daily_target=daily_target,
            applied_today=applied_today,
            remaining_today=max(0, daily_target - applied_today),
            discovered_today=discovered_today,
            shortlisted_today=counts[QueueStatus.SHORTLISTED.value],
            skipped_today=counts[QueueStatus.SKIPPED.value],
        )

    def get(self, job_id: int) -> DiscoveredJobRecord:
        with get_connection(self.database_url) as connection:
            row = connection.execute("SELECT * FROM discovered_jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"Discovered job {job_id} not found")
        return self._to_record(row)

    def canonical_url(self, job_url: str | None) -> str | None:
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

    def dedupe_key(self, company: str, title: str, source: str, canonical_url: str | None) -> str:
        if canonical_url:
            return f"url:{canonical_url}"
        return "manual:" + "|".join(
            [
                self._normalize_token(company),
                self._normalize_token(title),
                self._normalize_token(source or "manual"),
            ]
        )

    def _normalize_status(self, status: QueueStatus | str) -> str:
        return status.value if isinstance(status, QueueStatus) else str(status)

    def _normalize_token(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())

    def _find_duplicate(self, connection, canonical_url: str | None, dedupe_key: str):
        if canonical_url:
            row = connection.execute(
                "SELECT * FROM discovered_jobs WHERE canonical_url = ?",
                (canonical_url,),
            ).fetchone()
            if row is not None:
                return row
        return connection.execute(
            "SELECT * FROM discovered_jobs WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()

    def _merge_duplicate(self, connection, row, values: dict, now: str):
        current = dict(row)
        updates: dict[str, object] = {}
        merge_fields = [
            "title",
            "company",
            "job_url",
            "canonical_url",
            "source",
            "location",
            "work_mode",
            "description",
            "required_skills",
            "fit_score",
            "recommendation",
        ]
        for field in merge_fields:
            incoming = values.get(field)
            existing = current.get(field)
            if self._has_value(incoming) and not self._has_value(existing):
                updates[field] = incoming
        if updates:
            updates["updated_at"] = now
            assignments = ", ".join(f"{field} = :{field}" for field in updates)
            connection.execute(
                f"UPDATE discovered_jobs SET {assignments} WHERE id = :id",
                {**updates, "id": current["id"]},
            )
            return connection.execute("SELECT * FROM discovered_jobs WHERE id = ?", (current["id"],)).fetchone()
        return row

    def _has_value(self, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip()) and value.strip() != "[]"
        return True

    def _to_record(self, row) -> DiscoveredJobRecord:
        data = dict(row)
        data["required_skills"] = json.loads(data["required_skills"] or "[]")
        return DiscoveredJobRecord.model_validate(data)


def get_discovery_queue_repository(settings: Settings = Depends(get_settings)) -> DiscoveryQueueRepository:
    return DiscoveryQueueRepository(settings.database_url)
