from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ContactSource(str, Enum):
    MANUAL = "manual"
    COMPANY_SITE = "company_site"
    GUESSED_PATTERN = "guessed_pattern"
    USER_ADDED = "user_added"


class OutreachChannel(str, Enum):
    LINKEDIN = "linkedin"
    EMAIL = "email"
    OTHER = "other"


class OutreachMessageType(str, Enum):
    INITIAL = "initial"
    FOLLOW_UP_1 = "follow_up_1"
    FOLLOW_UP_2 = "follow_up_2"


class OutreachStatus(str, Enum):
    DRAFTED = "drafted"
    SENT_MANUALLY = "sent_manually"
    REPLIED = "replied"
    NO_RESPONSE = "no_response"
    ARCHIVED = "archived"


class OutreachContactCreate(BaseModel):
    company: str
    name: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    source: ContactSource = ContactSource.MANUAL
    confidence_score: float = Field(default=0.7, ge=0, le=1)
    notes: str | None = None


class OutreachContactUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    source: ContactSource | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None
    archived: bool | None = None


class OutreachContactRecord(OutreachContactCreate):
    id: int
    archived: bool = False
    created_at: datetime
    updated_at: datetime


class OutreachContactListResponse(BaseModel):
    contacts: list[OutreachContactRecord]


class OutreachSearchSuggestionRequest(BaseModel):
    company: str
    role_title: str | None = None
    job_url: str | None = None


class EmailPatternGuess(BaseModel):
    pattern: str
    example: str
    confidence_score: float
    warning: str


class OutreachSearchSuggestionResponse(BaseModel):
    search_queries: list[str]
    company_domain: str | None = None
    guessed_email_patterns: list[EmailPatternGuess]
    warnings: list[str]


class OutreachMessageGenerateRequest(BaseModel):
    company: str
    role_title: str
    contact_name: str | None = None
    contact_title: str | None = None
    channel: OutreachChannel = OutreachChannel.LINKEDIN
    message_type: OutreachMessageType = OutreachMessageType.INITIAL
    job_queue_id: int | None = None
    application_id: int | None = None


class OutreachMessageGenerateResponse(BaseModel):
    message_text: str
    warnings: list[str]
    strongest_relevant_points: list[str]


class OutreachFollowUpMessageRequest(BaseModel):
    original_message: str
    company: str
    role_title: str
    days_since_first_message: int = Field(default=6, ge=0, le=365)
    channel: OutreachChannel = OutreachChannel.LINKEDIN
    contact_name: str | None = None


class OutreachRecordCreate(BaseModel):
    job_queue_id: int | None = None
    application_id: int | None = None
    apply_session_id: int | None = None
    contact_id: int | None = None
    channel: OutreachChannel
    message_type: OutreachMessageType = OutreachMessageType.INITIAL
    message_text: str
    status: OutreachStatus = OutreachStatus.DRAFTED
    follow_up_date: date | None = None


class OutreachRecordStatusUpdate(BaseModel):
    status: OutreachStatus
    follow_up_date: date | None = None


class OutreachRecordRecord(OutreachRecordCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class OutreachRecordListResponse(BaseModel):
    records: list[OutreachRecordRecord]


class OutreachDashboardResponse(BaseModel):
    drafted: int
    sent_manually: int
    replies: int
    no_response: int
    follow_ups_due_today: int
    overdue_follow_ups: int
    upcoming_follow_ups: int


class OutreachHistoryRecord(OutreachRecordRecord):
    company: str | None = None
    contact_name: str | None = None
    contact_title: str | None = None


class OutreachHistoryResponse(BaseModel):
    records: list[OutreachHistoryRecord]
