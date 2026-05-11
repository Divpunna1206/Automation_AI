from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.api.routes import get_analytics_service
from app.db.outreach_repository import OutreachRepository
from app.db.repository import ApplicationRepository
from app.db.resume_version_repository import ResumeVersionRepository
from app.db.sqlite import init_db
from app.main import app
from app.models.application import ApplicationSaveRequest, ApplicationStatus
from app.models.outreach import OutreachChannel, OutreachContactCreate, OutreachMessageType, OutreachRecordCreate, OutreachStatus
from app.models.resume import ResumeVersionStatus
from app.services.analytics import AnalyticsService


def seed_analytics_data(database_url: str) -> None:
    applications = ApplicationRepository(database_url)
    app_one = applications.save(
        ApplicationSaveRequest(
            company="Acme AI",
            title="AI Product Engineer",
            source="remoteok",
            fit_score=82,
            status=ApplicationStatus.INTERVIEW,
            job_url="https://example.com/acme-ai-product",
        )
    )
    applications.save(
        ApplicationSaveRequest(
            company="Beta Labs",
            title="Senior Full Stack Engineer",
            source="manual",
            fit_score=58,
            status=ApplicationStatus.REJECTED,
            job_url="https://example.com/beta-full-stack",
        )
    )
    applications.save(
        ApplicationSaveRequest(
            company="Gamma AI",
            title="AI Engineer",
            source="remoteok",
            fit_score=76,
            status=ApplicationStatus.SUBMITTED,
            job_url="https://example.com/gamma-ai",
        )
    )

    resumes = ResumeVersionRepository(database_url)
    selected = resumes.create(
        resume_version_id="ai-product-v1",
        application_id=app_one.id,
        title="AI Product Engineer",
        company="Acme AI",
        ats_score=88,
        matched_keywords=["python", "fastapi"],
        missing_keywords=["Docker", "Kubernetes"],
        file_path="resume.pdf",
    )
    resumes.select(selected.id)
    resumes.create(
        resume_version_id="full-stack-v1",
        title="Senior Full Stack Engineer",
        company="Beta Labs",
        ats_score=61,
        matched_keywords=["react"],
        missing_keywords=["Docker"],
        file_path="resume2.pdf",
    )
    resumes.update_status(2, ResumeVersionStatus.REVIEWED)

    outreach = OutreachRepository(database_url)
    contact = outreach.create_contact(OutreachContactCreate(company="Acme AI", name="Asha"))
    outreach.create_record(
        OutreachRecordCreate(
            contact_id=contact.id,
            application_id=app_one.id,
            channel=OutreachChannel.LINKEDIN,
            message_text="Initial manual draft",
            status=OutreachStatus.REPLIED,
            follow_up_date=date.today() - timedelta(days=1),
        )
    )
    outreach.create_record(
        OutreachRecordCreate(
            contact_id=contact.id,
            application_id=app_one.id,
            channel=OutreachChannel.EMAIL,
            message_type=OutreachMessageType.FOLLOW_UP_1,
            message_text="Follow-up manual draft",
            status=OutreachStatus.NO_RESPONSE,
            follow_up_date=date.today(),
        )
    )


def test_analytics_aggregation_and_recommendations(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'analytics.db'}"
    init_db(database_url)
    seed_analytics_data(database_url)
    service = AnalyticsService(database_url)

    overview = service.overview()
    assert overview.total_applications == 3
    assert overview.average_ats_score == 73.0
    assert overview.interview_rate == 33.3
    assert overview.rejection_rate == 33.3
    assert overview.outreach_reply_rate == 50.0
    assert overview.best_performing_resume_version == "ai-product-v1 (AI Product Engineer)"
    assert overview.best_performing_job_source == "remoteok (2/2 positive outcomes)"
    assert overview.most_common_rejected_role_category == "full stack"

    gaps = service.skill_gaps()
    assert gaps.top_missing_skills[0].skill == "docker"
    assert gaps.top_missing_skills[0].count == 2
    assert gaps.top_missing_skills[0].percentage == 100.0

    outreach = service.outreach_performance()
    assert outreach.reply_rate == 50.0
    assert outreach.follow_up_reply_rate == 0.0
    assert {item.label for item in outreach.by_channel} == {"email", "linkedin"}

    recommendations = service.recommendations()
    assert "docker" in recommendations.skill_learning_priorities
    assert recommendations.next_best_actions
    assert recommendations.outreach_suggestions


def test_weekly_insights_are_grounded_and_handle_small_samples(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'small_analytics.db'}"
    init_db(database_url)
    ApplicationRepository(database_url).save(
        ApplicationSaveRequest(
            company="Acme AI",
            title="AI Engineer",
            source="manual",
            fit_score=70,
            status=ApplicationStatus.REVIEWED,
            job_url="https://example.com/small",
        )
    )
    service = AnalyticsService(database_url)

    insights = service.weekly_insights()
    assert insights.sample_size == 1
    assert any("Sample size is small (1 applications)" in item for item in insights.insights)
    text = " ".join(insights.insights)
    assert "63%" not in text
    assert "RemoteOK applications have higher" not in text


def test_analytics_dashboard_routes(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'analytics_routes.db'}"
    init_db(database_url)
    seed_analytics_data(database_url)
    service = AnalyticsService(database_url)
    app.dependency_overrides[get_analytics_service] = lambda: service
    client = TestClient(app)

    try:
        overview = client.get("/analytics/overview")
        assert overview.status_code == 200
        assert overview.json()["total_applications"] == 3

        gaps = client.get("/analytics/skills-gaps")
        assert gaps.status_code == 200
        assert gaps.json()["top_missing_skills"][0]["skill"] == "docker"

        resumes = client.get("/analytics/resume-performance")
        assert resumes.status_code == 200
        assert resumes.json()["best_performing_resume_version"] == "ai-product-v1 (AI Product Engineer)"

        outreach = client.get("/analytics/outreach-performance")
        assert outreach.status_code == 200
        assert outreach.json()["reply_rate"] == 50.0

        insights = client.get("/analytics/weekly-insights")
        assert insights.status_code == 200
        assert insights.json()["insights"]

        recommendations = client.get("/analytics/recommendations")
        assert recommendations.status_code == 200
        assert recommendations.json()["next_best_actions"]
    finally:
        app.dependency_overrides.clear()
