from pydantic import BaseModel, Field, HttpUrl


class JobAnalyzeRequest(BaseModel):
    title: str
    company: str
    description: str
    url: HttpUrl | None = None
    location: str | None = None
    source: str = "manual"


class ParsedJob(BaseModel):
    title: str
    company: str
    description: str
    url: str | None = None
    location: str | None = None
    source: str = "manual"
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    seniority: str | None = None
    employment_type: str | None = None
    tools: list[str] = Field(default_factory=list)
    domain_keywords: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    company_reputation: int | None = Field(default=None, ge=0, le=100)


class JobAnalyzeResponse(BaseModel):
    job: ParsedJob


class FitScore(BaseModel):
    score: int = Field(ge=0, le=100)
    recommendation: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    rationale: str
    signals: dict[str, int] = Field(default_factory=dict)


class JobScoreRequest(BaseModel):
    job: ParsedJob


class JobScoreResponse(BaseModel):
    score: FitScore


class JobSearchRequest(BaseModel):
    query: str = "AI Product Engineer"
    location: str | None = "Remote"
    sources: list[str] = Field(default_factory=lambda: ["remoteok", "manual"])
    manual_urls: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=50)


class JobListing(BaseModel):
    title: str
    company: str
    description: str
    url: str | None = None
    location: str | None = None
    source: str
    tags: list[str] = Field(default_factory=list)
    seniority: str | None = None
    company_reputation: int | None = Field(default=None, ge=0, le=100)


class ScoredJobListing(BaseModel):
    listing: JobListing
    parsed_job: ParsedJob
    score: FitScore


class JobSearchResponse(BaseModel):
    results: list[ScoredJobListing]
    source_errors: dict[str, str] = Field(default_factory=dict)
