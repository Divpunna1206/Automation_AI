from pydantic import BaseModel


class CountItem(BaseModel):
    label: str
    count: int


class RateMetric(BaseModel):
    label: str
    numerator: int
    denominator: int
    rate: float | None = None


class ResumePerformanceItem(BaseModel):
    resume_version_id: str
    title: str
    company: str
    usage_count: int
    ats_score: int
    status: str
    success_count: int


class OutreachPerformanceResponse(BaseModel):
    total_records: int
    drafted: int
    sent_manually: int
    replies: int
    no_response: int
    reply_rate: float | None
    follow_up_reply_rate: float | None
    by_channel: list[RateMetric]


class AnalyticsOverviewResponse(BaseModel):
    total_applications: int
    applications_by_status: list[CountItem]
    applications_by_source: list[CountItem]
    applications_by_role: list[CountItem]
    applications_by_ats_score_range: list[CountItem]
    applications_by_company: list[CountItem]
    response_rate: float | None
    interview_rate: float | None
    shortlisted_rate: float | None
    rejection_rate: float | None
    outreach_reply_rate: float | None
    average_ats_score: float | None
    best_performing_resume_version: str | None
    best_performing_job_source: str | None
    most_common_rejected_role_category: str | None


class SkillGapItem(BaseModel):
    skill: str
    count: int
    percentage: float


class SkillGapsResponse(BaseModel):
    total_resume_versions: int
    total_missing_keyword_mentions: int
    top_missing_skills: list[SkillGapItem]


class ResumePerformanceResponse(BaseModel):
    versions: list[ResumePerformanceItem]
    selected_resume_success: list[ResumePerformanceItem]
    best_performing_resume_version: str | None


class WeeklyInsightsResponse(BaseModel):
    sample_size: int
    insights: list[str]


class RecommendationsResponse(BaseModel):
    next_best_actions: list[str]
    resume_improvement_suggestions: list[str]
    outreach_suggestions: list[str]
    role_targeting_suggestions: list[str]
    follow_up_suggestions: list[str]
    skill_learning_priorities: list[str]
