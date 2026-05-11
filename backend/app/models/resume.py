from enum import Enum

from pydantic import BaseModel

from app.models.ats import ATSAnalyzeResponse
from app.models.job import FitScore, ParsedJob


class ResumeGenerateRequest(BaseModel):
    job: ParsedJob
    fit_score: FitScore | None = None


class ResumeGenerateResponse(BaseModel):
    resume_markdown: str
    resume_version: str
    pdf_path: str | None = None
    docx_path: str | None = None
    truthful_constraints: list[str]


class ResumeGenerateTailoredRequest(BaseModel):
    job: ParsedJob | None = None
    title: str | None = None
    company: str | None = None
    description: str | None = None
    job_queue_id: int | None = None
    application_id: int | None = None


class ResumeVersionStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    SELECTED = "selected"
    ARCHIVED = "archived"


class ResumeVersionStatusUpdateRequest(BaseModel):
    status: ResumeVersionStatus


class ResumeVersionRecord(BaseModel):
    id: int
    resume_version_id: str
    job_queue_id: int | None = None
    application_id: int | None = None
    title: str
    company: str
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    file_path: str | None = None
    file_path_docx: str | None = None
    status: ResumeVersionStatus = ResumeVersionStatus.DRAFT
    created_at: str


class ResumeVersionListResponse(BaseModel):
    versions: list[ResumeVersionRecord]


class TailoredResumeGenerateResponse(ResumeGenerateResponse):
    ats: ATSAnalyzeResponse
    version_record: ResumeVersionRecord
