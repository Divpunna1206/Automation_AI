from pydantic import BaseModel

from app.models.application import ApplicationRecord


class DashboardStatsResponse(BaseModel):
    total_jobs: int
    average_fit_score: float | None
    due_follow_ups: int
    status_counts: dict[str, int]
    recent_applications: list[ApplicationRecord]
