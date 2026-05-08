from pydantic import BaseModel

from app.models.job import ParsedJob


class CoverLetterRequest(BaseModel):
    job: ParsedJob
    resume_version: str | None = None


class CoverLetterResponse(BaseModel):
    cover_letter: str
    cautions: list[str]
