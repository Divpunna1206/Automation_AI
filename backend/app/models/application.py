from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    DISCOVERED = "discovered"
    REVIEWED = "reviewed"
    MATERIALS_GENERATED = "materials_generated"
    APPROVED = "approved"
    FORM_PREPARED = "form_prepared"
    APPLIED = "applied"
    SUBMITTED = "submitted"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"
    SKIPPED = "skipped"


STATUS_ORDER = [
    ApplicationStatus.DISCOVERED,
    ApplicationStatus.REVIEWED,
    ApplicationStatus.MATERIALS_GENERATED,
    ApplicationStatus.APPROVED,
    ApplicationStatus.FORM_PREPARED,
    ApplicationStatus.APPLIED,
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.REJECTED,
    ApplicationStatus.OFFER,
    ApplicationStatus.SKIPPED,
]


class ApplicationSaveRequest(BaseModel):
    company: str
    title: str
    job_url: str | None = None
    source: str = "manual"
    fit_score: int | None = Field(default=None, ge=0, le=100)
    recommendation: str | None = None
    resume_version: str | None = None
    resume_markdown: str | None = None
    resume_pdf_path: str | None = None
    cover_letter: str | None = None
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    follow_up_date: date | None = None
    notes: str | None = None


class ApplicationRecord(ApplicationSaveRequest):
    id: int
    discovered_at: datetime | None = None
    reviewed_at: datetime | None = None
    materials_generated_at: datetime | None = None
    approved_at: datetime | None = None
    form_prepared_at: datetime | None = None
    submitted_at: datetime | None = None
    interview_at: datetime | None = None
    rejected_at: datetime | None = None
    offer_at: datetime | None = None
    skipped_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationSaveResponse(BaseModel):
    application: ApplicationRecord


class ApplicationStatusUpdateRequest(BaseModel):
    status: ApplicationStatus
    follow_up_date: date | None = None
    notes: str | None = None


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationRecord]
