from pydantic import BaseModel, Field

from app.models.job import ParsedJob


class ATSAnalyzeRequest(BaseModel):
    job: ParsedJob | None = None
    title: str | None = None
    company: str | None = None
    description: str | None = None
    job_queue_id: int | None = None
    application_id: int | None = None


class GapActionItem(BaseModel):
    skill: str
    gap_type: str
    priority: str
    safe_resume_action: str
    learning_action: str
    interview_preparation_note: str


class GapActionPlanRequest(BaseModel):
    job: ParsedJob | None = None
    missing_keywords: list[str] = Field(default_factory=list)
    job_queue_id: int | None = None
    application_id: int | None = None


class GapActionPlanResponse(BaseModel):
    items: list[GapActionItem]
    safe_phrasing_suggestions: list[str]
    profile_update_suggestions: list[str]


class ATSAnalyzeResponse(BaseModel):
    ats_score: int = Field(ge=0, le=100)
    matched_keywords: list[str]
    missing_keywords: list[str]
    required_skills_detected: list[str]
    preferred_skills_detected: list[str]
    matched_projects: list[str]
    resume_gaps: list[str]
    recommended_resume_angle: str
    improvement_suggestions: list[str]
    missing_keyword_action_plan: list[GapActionItem]
    profile_update_suggestions: list[str]
    safe_phrasing_suggestions: list[str]
    warnings: list[str]
    truthfulness_notes: list[str]
    job: ParsedJob
