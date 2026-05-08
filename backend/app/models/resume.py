from pydantic import BaseModel

from app.models.job import FitScore, ParsedJob


class ResumeGenerateRequest(BaseModel):
    job: ParsedJob
    fit_score: FitScore | None = None


class ResumeGenerateResponse(BaseModel):
    resume_markdown: str
    resume_version: str
    pdf_path: str | None = None
    truthful_constraints: list[str]
