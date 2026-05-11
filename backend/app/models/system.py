from pydantic import BaseModel


class SystemHealthCheckResponse(BaseModel):
    backend_status: str
    database_reachable: bool
    config_valid: bool
    artifacts_writable: bool
    playwright_status: str
    llm_status: str
    frontend_api_base_url_suggestion: str
    warnings: list[str]


class DemoSeedResponse(BaseModel):
    created_jobs: int
    created_applications: int
    created_resume_versions: int
    created_contacts: int
    created_outreach_records: int
    message: str
