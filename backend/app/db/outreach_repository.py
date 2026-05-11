from datetime import date, datetime, timedelta

from fastapi import Depends

from app.core.settings import Settings, get_settings
from app.db.sqlite import get_connection
from app.models.outreach import (
    OutreachContactCreate,
    OutreachContactListResponse,
    OutreachContactRecord,
    OutreachContactUpdate,
    OutreachDashboardResponse,
    OutreachHistoryRecord,
    OutreachHistoryResponse,
    OutreachChannel,
    OutreachRecordCreate,
    OutreachRecordListResponse,
    OutreachRecordRecord,
    OutreachRecordStatusUpdate,
    OutreachStatus,
)


class OutreachRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def create_contact(self, payload: OutreachContactCreate) -> OutreachContactRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        values = payload.model_dump()
        values["source"] = values["source"].value
        with get_connection(self.database_url) as connection:
            cursor = connection.execute(
                """
                INSERT INTO outreach_contacts (
                    company, name, title, linkedin_url, email, source,
                    confidence_score, notes, archived, created_at, updated_at
                ) VALUES (
                    :company, :name, :title, :linkedin_url, :email, :source,
                    :confidence_score, :notes, 0, :created_at, :updated_at
                )
                """,
                {**values, "created_at": now, "updated_at": now},
            )
            row = connection.execute("SELECT * FROM outreach_contacts WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._contact(row)

    def list_contacts(self, company: str | None = None, include_archived: bool = False) -> OutreachContactListResponse:
        clauses = []
        params: list[object] = []
        if company:
            clauses.append("LOWER(company) = LOWER(?)")
            params.append(company)
        if not include_archived:
            clauses.append("archived = 0")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with get_connection(self.database_url) as connection:
            rows = connection.execute(
                f"SELECT * FROM outreach_contacts {where} ORDER BY updated_at DESC",
                params,
            ).fetchall()
        return OutreachContactListResponse(contacts=[self._contact(row) for row in rows])

    def update_contact(self, contact_id: int, payload: OutreachContactUpdate) -> OutreachContactRecord:
        current = self.get_contact(contact_id)
        data = current.model_dump()
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            if key == "archived":
                continue
            if value is not None:
                data[key] = value.value if hasattr(value, "value") else value
        data["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
        data["id"] = contact_id
        with get_connection(self.database_url) as connection:
            connection.execute(
                """
                UPDATE outreach_contacts
                SET name = :name, title = :title, linkedin_url = :linkedin_url,
                    email = :email, source = :source, confidence_score = :confidence_score,
                    notes = :notes, updated_at = :updated_at
                WHERE id = :id
                """,
                data,
            )
            row = connection.execute("SELECT * FROM outreach_contacts WHERE id = ?", (contact_id,)).fetchone()
        return self._contact(row)

    def archive_contact(self, contact_id: int) -> OutreachContactRecord:
        with get_connection(self.database_url) as connection:
            connection.execute(
                "UPDATE outreach_contacts SET archived = 1, updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(timespec="seconds"), contact_id),
            )
            row = connection.execute("SELECT * FROM outreach_contacts WHERE id = ?", (contact_id,)).fetchone()
        if row is None:
            raise ValueError(f"Outreach contact {contact_id} not found")
        return self._contact(row)

    def get_contact(self, contact_id: int) -> OutreachContactRecord:
        with get_connection(self.database_url) as connection:
            row = connection.execute("SELECT * FROM outreach_contacts WHERE id = ?", (contact_id,)).fetchone()
        if row is None:
            raise ValueError(f"Outreach contact {contact_id} not found")
        return self._contact(row)

    def create_record(self, payload: OutreachRecordCreate) -> OutreachRecordRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        values = payload.model_dump()
        values["channel"] = values["channel"].value
        values["message_type"] = values["message_type"].value
        values["status"] = values["status"].value
        if values["follow_up_date"] is None and values["status"] == OutreachStatus.DRAFTED.value:
            values["follow_up_date"] = (date.today() + timedelta(days=6)).isoformat()
        elif values["follow_up_date"] is not None:
            values["follow_up_date"] = values["follow_up_date"].isoformat()
        with get_connection(self.database_url) as connection:
            cursor = connection.execute(
                """
                INSERT INTO outreach_records (
                    job_queue_id, application_id, apply_session_id, contact_id,
                    channel, message_type, message_text, status, follow_up_date,
                    created_at, updated_at
                ) VALUES (
                    :job_queue_id, :application_id, :apply_session_id, :contact_id,
                    :channel, :message_type, :message_text, :status, :follow_up_date,
                    :created_at, :updated_at
                )
                """,
                {**values, "created_at": now, "updated_at": now},
            )
            row = connection.execute("SELECT * FROM outreach_records WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._record(row)

    def list_records(self, status: OutreachStatus | None = None) -> OutreachRecordListResponse:
        with get_connection(self.database_url) as connection:
            if status:
                rows = connection.execute(
                    "SELECT * FROM outreach_records WHERE status = ? ORDER BY updated_at DESC",
                    (status.value,),
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM outreach_records ORDER BY updated_at DESC").fetchall()
        return OutreachRecordListResponse(records=[self._record(row) for row in rows])

    def update_record_status(self, record_id: int, payload: OutreachRecordStatusUpdate) -> OutreachRecordRecord:
        follow_up = payload.follow_up_date.isoformat() if payload.follow_up_date else None
        with get_connection(self.database_url) as connection:
            connection.execute(
                """
                UPDATE outreach_records
                SET status = ?, follow_up_date = COALESCE(?, follow_up_date), updated_at = ?
                WHERE id = ?
                """,
                (payload.status.value, follow_up, datetime.utcnow().isoformat(timespec="seconds"), record_id),
            )
            row = connection.execute("SELECT * FROM outreach_records WHERE id = ?", (record_id,)).fetchone()
        if row is None:
            raise ValueError(f"Outreach record {record_id} not found")
        return self._record(row)

    def dashboard(self) -> OutreachDashboardResponse:
        today = date.today().isoformat()
        active_statuses = (OutreachStatus.DRAFTED.value, OutreachStatus.SENT_MANUALLY.value, OutreachStatus.NO_RESPONSE.value)
        with get_connection(self.database_url) as connection:
            status_rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM outreach_records GROUP BY status"
            ).fetchall()
            status_counts = {row["status"]: row["count"] for row in status_rows}
            due_today = connection.execute(
                """
                SELECT COUNT(*) AS count FROM outreach_records
                WHERE follow_up_date = ? AND status IN (?, ?, ?)
                """,
                (today, *active_statuses),
            ).fetchone()["count"]
            overdue = connection.execute(
                """
                SELECT COUNT(*) AS count FROM outreach_records
                WHERE follow_up_date < ? AND status IN (?, ?, ?)
                """,
                (today, *active_statuses),
            ).fetchone()["count"]
            upcoming = connection.execute(
                """
                SELECT COUNT(*) AS count FROM outreach_records
                WHERE follow_up_date > ? AND status IN (?, ?, ?)
                """,
                (today, *active_statuses),
            ).fetchone()["count"]
        return OutreachDashboardResponse(
            drafted=status_counts.get(OutreachStatus.DRAFTED.value, 0),
            sent_manually=status_counts.get(OutreachStatus.SENT_MANUALLY.value, 0),
            replies=status_counts.get(OutreachStatus.REPLIED.value, 0),
            no_response=status_counts.get(OutreachStatus.NO_RESPONSE.value, 0),
            follow_ups_due_today=due_today,
            overdue_follow_ups=overdue,
            upcoming_follow_ups=upcoming,
        )

    def follow_ups(
        self,
        due_today: bool = False,
        overdue: bool = False,
        upcoming: bool = False,
        company: str | None = None,
        channel: OutreachChannel | None = None,
        status: OutreachStatus | None = None,
    ) -> OutreachHistoryResponse:
        today = date.today().isoformat()
        clauses = ["r.follow_up_date IS NOT NULL"]
        params: list[object] = []
        if due_today:
            clauses.append("r.follow_up_date = ?")
            params.append(today)
        if overdue:
            clauses.append("r.follow_up_date < ?")
            params.append(today)
        if upcoming:
            clauses.append("r.follow_up_date > ?")
            params.append(today)
        if company:
            clauses.append("LOWER(c.company) = LOWER(?)")
            params.append(company)
        if channel:
            clauses.append("r.channel = ?")
            params.append(channel.value)
        if status:
            clauses.append("r.status = ?")
            params.append(status.value)
        if not status:
            clauses.append("r.status NOT IN (?, ?)")
            params.extend([OutreachStatus.REPLIED.value, OutreachStatus.ARCHIVED.value])
        return self._joined_records(clauses, params, order_by="r.follow_up_date ASC, r.updated_at DESC")

    def history(
        self,
        contact_id: int | None = None,
        company: str | None = None,
        application_id: int | None = None,
        job_queue_id: int | None = None,
    ) -> OutreachHistoryResponse:
        clauses = []
        params: list[object] = []
        if contact_id is not None:
            clauses.append("r.contact_id = ?")
            params.append(contact_id)
        if company:
            clauses.append("LOWER(c.company) = LOWER(?)")
            params.append(company)
        if application_id is not None:
            clauses.append("r.application_id = ?")
            params.append(application_id)
        if job_queue_id is not None:
            clauses.append("r.job_queue_id = ?")
            params.append(job_queue_id)
        return self._joined_records(clauses, params, order_by="r.created_at DESC, r.id DESC")

    def _joined_records(self, clauses: list[str], params: list[object], order_by: str) -> OutreachHistoryResponse:
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with get_connection(self.database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT r.*, c.company AS company, c.name AS contact_name, c.title AS contact_title
                FROM outreach_records r
                LEFT JOIN outreach_contacts c ON c.id = r.contact_id
                {where}
                ORDER BY {order_by}
                """,
                params,
            ).fetchall()
        return OutreachHistoryResponse(records=[self._history_record(row) for row in rows])

    def _contact(self, row) -> OutreachContactRecord:
        data = dict(row)
        data["archived"] = bool(data["archived"])
        return OutreachContactRecord.model_validate(data)

    def _record(self, row) -> OutreachRecordRecord:
        return OutreachRecordRecord.model_validate(dict(row))

    def _history_record(self, row) -> OutreachHistoryRecord:
        return OutreachHistoryRecord.model_validate(dict(row))


def get_outreach_repository(settings: Settings = Depends(get_settings)) -> OutreachRepository:
    return OutreachRepository(settings.database_url)
