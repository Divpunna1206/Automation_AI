from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.form import FillField


class ApplySessionStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    REVIEW_REQUIRED = "review_required"
    COMPLETED_MANUALLY = "completed_manually"
    FAILED = "failed"
    SKIPPED = "skipped"


class FieldResult(BaseModel):
    label: str
    status: str
    message: str
    selector: str | None = None
    confidence: str = "medium"


class ApplySessionCreateRequest(BaseModel):
    job_queue_id: int | None = None
    application_id: int | None = None
    job_url: str | None = None
    company: str | None = None
    title: str | None = None
    resume_version_id: int | None = None
    resume_file_path: str | None = None
    cover_letter_text: str | None = None


class ApplySessionStatusUpdateRequest(BaseModel):
    message: str | None = None


class ApplySessionRecord(BaseModel):
    id: int
    job_queue_id: int | None = None
    application_id: int | None = None
    job_url: str
    company: str
    title: str
    resume_version_id: int | None = None
    resume_file_path: str | None = None
    cover_letter_text: str | None = None
    status: ApplySessionStatus
    fill_summary: str | None = None
    field_results: list[FieldResult] = Field(default_factory=list)
    screenshot_paths: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApplyQuestionUpdateRequest(BaseModel):
    answer_text: str | None = None
    requires_manual_review: bool | None = None


class ApplySessionQuestionRecord(BaseModel):
    id: int
    apply_session_id: int
    question_text: str
    detected_field_label: str | None = None
    answer_text: str | None = None
    confidence_score: float = Field(ge=0, le=1)
    answer_source: str
    requires_manual_review: bool
    created_at: datetime
    updated_at: datetime


class ApplySessionQuestionListResponse(BaseModel):
    questions: list[ApplySessionQuestionRecord]


class ApplySessionReviewPack(BaseModel):
    session: ApplySessionRecord
    selected_resume_version: int | None = None
    resume_file_path: str | None = None
    cover_letter: str | None = None
    field_fill_summary: str | None = None
    unanswered_questions: list[ApplySessionQuestionRecord]
    generated_answers: list[ApplySessionQuestionRecord]
    warnings: list[str]
    screenshots: list[str]
    final_manual_checklist: list[str]


class ApplySessionListResponse(BaseModel):
    sessions: list[ApplySessionRecord]


class ApplySessionCreateResponse(BaseModel):
    session: ApplySessionRecord
    fill_plan: list[FillField]
    message: str
