from datetime import date

from app.db.repository import ApplicationRepository
from app.db.sqlite import init_db
from app.models.application import (
    ApplicationSaveRequest,
    ApplicationStatus,
    ApplicationStatusUpdateRequest,
)


def test_application_lifecycle_tracking(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'applications.db'}"
    init_db(database_url)
    repository = ApplicationRepository(database_url)

    saved = repository.save(
        ApplicationSaveRequest(
            company="Acme AI",
            title="AI Product Engineer",
            status=ApplicationStatus.REVIEWED,
            fit_score=82,
        )
    )

    assert saved.status == ApplicationStatus.REVIEWED
    assert saved.discovered_at is not None
    assert saved.reviewed_at is not None

    updated = repository.update_status(
        saved.id,
        ApplicationStatusUpdateRequest(
            status=ApplicationStatus.SUBMITTED,
            follow_up_date=date(2026, 5, 10),
            notes="Manual submission completed.",
        ),
    )

    assert updated.status == ApplicationStatus.SUBMITTED
    assert updated.submitted_at is not None
    assert str(updated.follow_up_date) == "2026-05-10"

    stats = repository.dashboard_stats()
    assert stats.total_jobs == 1
    assert stats.status_counts["submitted"] == 1


def test_application_save_dedupes_by_canonical_job_url(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'applications.db'}"
    init_db(database_url)
    repository = ApplicationRepository(database_url)

    first = repository.save(
        ApplicationSaveRequest(
            company="Acme AI",
            title="AI Product Engineer",
            job_url="https://example.com/jobs/123?utm_source=newsletter",
            source="remoteok",
            fit_score=82,
        )
    )
    duplicate = repository.save(
        ApplicationSaveRequest(
            company="Acme AI",
            title="AI Product Engineer",
            job_url="https://example.com/jobs/123",
            source="remoteok",
            fit_score=90,
        )
    )

    assert duplicate.id == first.id
    assert repository.dashboard_stats().total_jobs == 1


def test_application_save_dedupes_by_company_title_source_when_url_missing(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'applications.db'}"
    init_db(database_url)
    repository = ApplicationRepository(database_url)

    first = repository.save(
        ApplicationSaveRequest(
            company="Acme AI",
            title="AI Product Engineer",
            source="manual",
            fit_score=82,
        )
    )
    duplicate = repository.save(
        ApplicationSaveRequest(
            company=" acme ai ",
            title="AI   Product Engineer",
            source="manual",
            fit_score=90,
        )
    )

    assert duplicate.id == first.id
    assert repository.dashboard_stats().total_jobs == 1
