from datetime import datetime

from fastapi import Depends

from app.core.settings import Settings, get_settings
from app.db.sqlite import get_connection
from app.models.apply_session import ApplySessionQuestionListResponse, ApplySessionQuestionRecord


class ApplyQuestionRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def create(
        self,
        apply_session_id: int,
        question_text: str,
        detected_field_label: str | None,
        answer_text: str | None,
        confidence_score: float,
        answer_source: str,
        requires_manual_review: bool,
    ) -> ApplySessionQuestionRecord:
        now = datetime.utcnow().isoformat(timespec="seconds")
        with get_connection(self.database_url) as connection:
            cursor = connection.execute(
                """
                INSERT INTO apply_session_questions (
                    apply_session_id, question_text, detected_field_label, answer_text,
                    confidence_score, answer_source, requires_manual_review, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    apply_session_id,
                    question_text,
                    detected_field_label,
                    answer_text,
                    confidence_score,
                    answer_source,
                    1 if requires_manual_review else 0,
                    now,
                    now,
                ),
            )
            row = connection.execute("SELECT * FROM apply_session_questions WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_record(row)

    def list_for_session(self, apply_session_id: int) -> ApplySessionQuestionListResponse:
        with get_connection(self.database_url) as connection:
            rows = connection.execute(
                "SELECT * FROM apply_session_questions WHERE apply_session_id = ? ORDER BY id",
                (apply_session_id,),
            ).fetchall()
        return ApplySessionQuestionListResponse(questions=[self._to_record(row) for row in rows])

    def update(self, question_id: int, answer_text: str | None, requires_manual_review: bool | None) -> ApplySessionQuestionRecord:
        current = self.get(question_id)
        with get_connection(self.database_url) as connection:
            connection.execute(
                """
                UPDATE apply_session_questions
                SET answer_text = ?,
                    requires_manual_review = ?,
                    answer_source = 'manual_required',
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    answer_text if answer_text is not None else current.answer_text,
                    1 if (requires_manual_review if requires_manual_review is not None else current.requires_manual_review) else 0,
                    datetime.utcnow().isoformat(timespec="seconds"),
                    question_id,
                ),
            )
            row = connection.execute("SELECT * FROM apply_session_questions WHERE id = ?", (question_id,)).fetchone()
        return self._to_record(row)

    def get(self, question_id: int) -> ApplySessionQuestionRecord:
        with get_connection(self.database_url) as connection:
            row = connection.execute("SELECT * FROM apply_session_questions WHERE id = ?", (question_id,)).fetchone()
        if row is None:
            raise ValueError(f"Apply question {question_id} not found")
        return self._to_record(row)

    def _to_record(self, row) -> ApplySessionQuestionRecord:
        data = dict(row)
        data["requires_manual_review"] = bool(data["requires_manual_review"])
        return ApplySessionQuestionRecord.model_validate(data)


def get_apply_question_repository(settings: Settings = Depends(get_settings)) -> ApplyQuestionRepository:
    return ApplyQuestionRepository(settings.database_url)
