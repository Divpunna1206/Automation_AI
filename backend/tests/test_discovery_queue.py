from app.core.config_loader import Answers, Preferences, Profile, ProfileBundle
from app.core.settings import Settings
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.db.sqlite import init_db
from app.models.job_queue import DiscoveredJobSaveRequest, JobDiscoverRequest, JobQueueFilters, QueueStatus
from app.services.job_queue_service import JobQueueService


def profile_bundle() -> ProfileBundle:
    return ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            summary="Full-stack AI engineer",
            skills=["Python", "FastAPI", "React", "SQL"],
        ),
        preferences=Preferences(
            target_titles=["AI Engineer"],
            target_locations=["Remote"],
            daily_application_target=2,
            preferred_keywords=["FastAPI"],
        ),
        answers=Answers(),
    )


def queue_payload(**overrides) -> DiscoveredJobSaveRequest:
    values = {
        "title": "AI Engineer",
        "company": "Acme AI",
        "job_url": "https://example.com/jobs/123?utm_source=test",
        "source": "manual",
        "location": "Remote",
        "work_mode": "remote",
        "description": "Build FastAPI and React services.",
        "required_skills": ["fastapi", "react"],
        "fit_score": 88,
        "recommendation": "approve",
    }
    values.update(overrides)
    return DiscoveredJobSaveRequest(**values)


def test_queue_dedupes_by_canonical_url(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    repository = DiscoveryQueueRepository(database_url)

    first = repository.save_discovered_job(queue_payload())
    duplicate = repository.save_discovered_job(queue_payload(job_url="https://example.com/jobs/123"))

    assert first.created is True
    assert duplicate.created is False
    assert duplicate.job.id == first.job.id
    assert len(repository.list_discovered_jobs().jobs) == 1


def test_queue_dedupes_without_url_by_company_title_source(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    repository = DiscoveryQueueRepository(database_url)

    first = repository.save_discovered_job(queue_payload(job_url=None))
    duplicate = repository.save_discovered_job(
        queue_payload(job_url=None, company=" acme ai ", title="AI   Engineer", source="manual")
    )

    assert first.created is True
    assert duplicate.created is False
    assert duplicate.job.id == first.job.id
    assert len(repository.list_discovered_jobs().jobs) == 1


def test_queue_status_updates_and_daily_target_stats(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    repository = DiscoveryQueueRepository(database_url)
    saved = repository.save_discovered_job(queue_payload()).job

    shortlisted = repository.shortlist_job(saved.id)
    assert shortlisted.queue_status == QueueStatus.SHORTLISTED
    skipped = repository.skip_job(saved.id)
    assert skipped.queue_status == QueueStatus.SKIPPED

    stats = repository.get_daily_target_stats(daily_target=2)
    assert stats.daily_target == 2
    assert stats.discovered_today == 1
    assert stats.skipped_today == 1
    assert stats.remaining_today == 2


def test_convert_queue_job_to_application_marks_applied(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    queue_repository = DiscoveryQueueRepository(database_url)
    application_repository = ApplicationRepository(database_url)
    saved = queue_repository.save_discovered_job(queue_payload()).job

    converted = queue_repository.convert_to_application(saved.id, application_repository)

    assert converted.queue_status == QueueStatus.APPLIED
    assert application_repository.dashboard_stats().total_jobs == 1
    stats = queue_repository.get_daily_target_stats(daily_target=2)
    assert stats.applied_today == 1
    assert stats.remaining_today == 1


def test_discover_saves_manual_jobs_and_counts_duplicates(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    service = JobQueueService(
        DiscoveryQueueRepository(database_url),
        ApplicationRepository(database_url),
        profile_bundle(),
        Settings(database_url=database_url),
    )
    request = JobDiscoverRequest(
        query="AI Engineer",
        location="Remote",
        sources=["manual"],
        manual_urls=["https://example.com/apply", "https://example.com/apply?utm_source=test"],
        limit=10,
    )

    first = service.discover(request)
    second = service.discover(request)

    assert first.inserted_count == 1
    assert first.duplicate_count == 1
    assert second.inserted_count == 0
    assert second.duplicate_count == 2
    assert len(service.list_discovered_jobs().jobs) == 1


def test_queue_filters_individually_and_combined(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    repository = DiscoveryQueueRepository(database_url)
    first = repository.save_discovered_job(queue_payload()).job
    repository.save_discovered_job(
        queue_payload(
            title="Backend Engineer",
            company="Beta Co",
            job_url="https://example.com/jobs/456",
            source="remoteok",
            location="Bengaluru Hybrid",
            work_mode="hybrid",
            description="Build Django systems.",
            required_skills=["django"],
            fit_score=55,
            recommendation="review",
        )
    )
    repository.shortlist_job(first.id)

    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(status=QueueStatus.SHORTLISTED)).jobs) == 1
    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(source="remoteok")).jobs) == 1
    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(min_fit_score=80)).jobs) == 1
    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(location="bengaluru")).jobs) == 1
    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(work_mode="remote")).jobs) == 1
    combined = repository.list_discovered_jobs(
        filters=JobQueueFilters(source="manual", min_fit_score=80, work_mode="remote", status=QueueStatus.SHORTLISTED)
    )
    assert [job.id for job in combined.jobs] == [first.id]


def test_queue_search_filter_matches_text_and_skills(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    repository = DiscoveryQueueRepository(database_url)
    repository.save_discovered_job(queue_payload())
    repository.save_discovered_job(
        queue_payload(
            title="Data Engineer",
            company="Data Co",
            job_url="https://example.com/jobs/data",
            description="Own pipelines.",
            required_skills=["airflow"],
            fit_score=40,
        )
    )

    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(search="Acme")).jobs) == 1
    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(search="FastAPI")).jobs) == 1
    assert len(repository.list_discovered_jobs(filters=JobQueueFilters(search="airflow")).jobs) == 1


def test_duplicate_merge_fills_missing_fields_without_overwriting_status(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue.db'}"
    init_db(database_url)
    repository = DiscoveryQueueRepository(database_url)
    first = repository.save_discovered_job(
        queue_payload(location=None, work_mode=None, required_skills=[], fit_score=None, recommendation=None)
    ).job
    repository.shortlist_job(first.id)

    duplicate = repository.save_discovered_job(
        queue_payload(
            location="Remote India",
            work_mode="remote",
            required_skills=["fastapi"],
            fit_score=91,
            recommendation="approve",
            queue_status=QueueStatus.SKIPPED,
        )
    ).job

    assert duplicate.id == first.id
    assert duplicate.location == "Remote India"
    assert duplicate.work_mode == "remote"
    assert duplicate.required_skills == ["fastapi"]
    assert duplicate.fit_score == 91
    assert duplicate.recommendation == "approve"
    assert duplicate.queue_status == QueueStatus.SHORTLISTED
