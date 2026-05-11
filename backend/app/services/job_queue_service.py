from app.core.config_loader import ProfileBundle
from app.core.settings import Settings
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.models.job_queue import (
    DailyTargetStatsResponse,
    DiscoveredJobListResponse,
    DiscoveredJobRecord,
    DiscoveredJobSaveRequest,
    JobDiscoverRequest,
    JobDiscoverResponse,
    JobQueueFilters,
    QueueStatus,
)
from app.services.fit_scorer import FitScorer
from app.services.job_discovery import JobDiscoveryService


class JobQueueService:
    def __init__(
        self,
        repository: DiscoveryQueueRepository,
        application_repository: ApplicationRepository,
        profile_bundle: ProfileBundle,
        settings: Settings,
    ):
        self.repository = repository
        self.application_repository = application_repository
        self.profile_bundle = profile_bundle
        self.settings = settings

    def discover(self, request: JobDiscoverRequest) -> JobDiscoverResponse:
        discovery = JobDiscoveryService(self.settings, FitScorer(self.profile_bundle)).search(request)
        jobs: list[DiscoveredJobRecord] = []
        inserted_count = 0
        duplicate_count = 0
        skipped_count = 0

        for item in discovery.results:
            listing = item.listing
            parsed = item.parsed_job
            if not listing.title or not listing.company:
                skipped_count += 1
                continue
            result = self.repository.save_discovered_job(
                DiscoveredJobSaveRequest(
                    title=listing.title,
                    company=listing.company,
                    job_url=listing.url,
                    source=listing.source,
                    location=listing.location,
                    work_mode=self._detect_work_mode(listing.location, listing.description),
                    description=listing.description,
                    required_skills=parsed.required_skills,
                    fit_score=item.score.score,
                    recommendation=item.score.recommendation,
                    queue_status=QueueStatus.DISCOVERED,
                )
            )
            jobs.append(result.job)
            if result.created:
                inserted_count += 1
            else:
                duplicate_count += 1

        return JobDiscoverResponse(
            jobs=jobs,
            inserted_count=inserted_count,
            duplicate_count=duplicate_count,
            skipped_count=skipped_count,
            source_errors=discovery.source_errors,
        )

    def save_discovered_job(self, payload: DiscoveredJobSaveRequest):
        return self.repository.save_discovered_job(payload)

    def list_discovered_jobs(self, filters: JobQueueFilters | None = None) -> DiscoveredJobListResponse:
        return self.repository.list_discovered_jobs(filters=filters)

    def update_queue_status(self, job_id: int, status: QueueStatus) -> DiscoveredJobRecord:
        return self.repository.update_queue_status(job_id, status)

    def shortlist_job(self, job_id: int) -> DiscoveredJobRecord:
        return self.repository.shortlist_job(job_id)

    def skip_job(self, job_id: int) -> DiscoveredJobRecord:
        return self.repository.skip_job(job_id)

    def convert_to_application(self, job_id: int) -> DiscoveredJobRecord:
        return self.repository.convert_to_application(job_id, self.application_repository)

    def get_daily_target_stats(self) -> DailyTargetStatsResponse:
        return self.repository.get_daily_target_stats(self.profile_bundle.preferences.daily_application_target)

    def _detect_work_mode(self, location: str | None, description: str) -> str | None:
        text = f"{location or ''} {description}".lower()
        if "remote" in text:
            return "remote"
        if "hybrid" in text:
            return "hybrid"
        if "onsite" in text or "on-site" in text:
            return "onsite"
        return None
