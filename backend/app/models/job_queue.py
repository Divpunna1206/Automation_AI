from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl

from app.models.job import JobSearchRequest


class QueueStatus(str, Enum):
    DISCOVERED = "discovered"
    SHORTLISTED = "shortlisted"
    SKIPPED = "skipped"
    APPLIED = "applied"


class DiscoveredJobSaveRequest(BaseModel):
    title: str
    company: str
    job_url: str | None = None
    source: str = "manual"
    location: str | None = None
    work_mode: str | None = None
    description: str
    required_skills: list[str] = Field(default_factory=list)
    fit_score: int | None = Field(default=None, ge=0, le=100)
    recommendation: str | None = None
    queue_status: QueueStatus = QueueStatus.DISCOVERED


class DiscoveredJobRecord(DiscoveredJobSaveRequest):
    id: int
    canonical_url: str | None = None
    discovered_at: datetime
    updated_at: datetime


class DiscoveredJobListResponse(BaseModel):
    jobs: list[DiscoveredJobRecord]


class JobQueueFilters(BaseModel):
    status: QueueStatus | None = None
    source: str | None = None
    min_fit_score: int | None = Field(default=None, ge=0, le=100)
    location: str | None = None
    work_mode: str | None = None
    search: str | None = None
    discovered_from: date | None = None
    discovered_to: date | None = None
    limit: int = Field(default=100, ge=1, le=200)


class QueueStatusUpdateRequest(BaseModel):
    queue_status: QueueStatus


class DiscoveredJobSaveResult(BaseModel):
    job: DiscoveredJobRecord
    created: bool


class JobDiscoverRequest(JobSearchRequest):
    pass


class JobDiscoverResponse(BaseModel):
    jobs: list[DiscoveredJobRecord]
    inserted_count: int
    duplicate_count: int
    skipped_count: int
    source_errors: dict[str, str] = Field(default_factory=dict)


class DailyTargetStatsResponse(BaseModel):
    daily_target: int
    applied_today: int
    remaining_today: int
    discovered_today: int
    shortlisted_today: int
    skipped_today: int


class JobParseUrlRequest(BaseModel):
    job_url: HttpUrl


class JobParseUrlResponse(BaseModel):
    title: str
    company: str
    job_url: str
    source: str
    location: str | None = None
    description: str
    message: str
