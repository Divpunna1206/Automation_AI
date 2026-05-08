from pydantic import BaseModel, Field


class FormFillRequest(BaseModel):
    application_url: str
    resume_path: str | None = None
    cover_letter: str | None = None
    dry_run: bool = True


class FillField(BaseModel):
    label: str
    value: str
    selector_candidates: list[str] = Field(default_factory=list)
    kind: str = "text"


class FormFillPlanResponse(BaseModel):
    application_url: str
    fields: list[FillField]
    requires_user_approval: bool = True
    can_submit: bool = False
    message: str


class FormFillRunResponse(BaseModel):
    status: str
    message: str
    requires_user_approval: bool = True
