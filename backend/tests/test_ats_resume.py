from fastapi.testclient import TestClient

from app.api.routes import (
    get_application_repository,
    get_discovery_queue_repository,
    get_resume_version_repository,
)
from app.core.config_loader import Answers, ExperienceItem, Preferences, Profile, ProfileBundle
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.db.resume_version_repository import ResumeVersionRepository
from app.db.sqlite import init_db
from app.models.ats import ATSAnalyzeRequest
from app.models.job import JobAnalyzeRequest
from app.models.job_queue import DiscoveredJobSaveRequest
from app.models.resume import ResumeGenerateTailoredRequest
from app.models.resume import ResumeVersionStatus
from app.services.ats_analyzer import ATSAnalyzer
from app.services.jd_parser import JDParser
from app.services.tailored_resume_service import TailoredResumeService
from app.main import app


def bundle() -> ProfileBundle:
    return ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            summary="Full-stack AI engineer",
            skills=["Python", "FastAPI", "React", "SQL", "OpenAI", "Playwright", "automation", "human-in-the-loop", "API", "AI"],
            experience=[
                ExperienceItem(
                    company="AI Co",
                    title="AI Engineer",
                    start="2022",
                    end="Present",
                    skills=["Python", "FastAPI", "React", "OpenAI", "Playwright", "automation", "human-in-the-loop"],
                    highlights=[
                        "Built FastAPI and React systems with OpenAI integrations.",
                        "Designed Playwright automations with human review gates.",
                    ],
                )
            ],
            education=["Test University"],
        ),
        preferences=Preferences(target_titles=["AI Engineer"], target_locations=["Remote"]),
        answers=Answers(),
    )


def parsed_job(description: str):
    return JDParser().parse(
        JobAnalyzeRequest(
            title="AI Engineer",
            company="Acme AI",
            description=description,
            location="Remote",
            source="test",
        )
    )


def test_ats_score_high_match() -> None:
    job = parsed_job("Required: Python, FastAPI, React, SQL, OpenAI. Build human-in-the-loop automation.")

    result = ATSAnalyzer(bundle()).analyze(ATSAnalyzeRequest(job=job))

    assert result.ats_score >= 80
    assert "fastapi" in result.matched_keywords
    assert result.resume_gaps == []


def test_ats_score_low_match_and_missing_keywords() -> None:
    job = parsed_job("Required: Kubernetes, Redis, GraphQL, AWS, LangChain. Bonus: FastAPI.")

    result = ATSAnalyzer(bundle()).analyze(ATSAnalyzeRequest(job=job))

    assert result.ats_score < 60
    assert "kubernetes" in result.missing_keywords
    assert any("below 60" in warning for warning in result.warnings)


def test_required_vs_preferred_extraction() -> None:
    job = parsed_job("Required: Python and FastAPI. Nice to have: GraphQL and Redis.")

    assert "python" in job.required_skills
    assert "fastapi" in job.required_skills
    assert "graphql" in job.preferred_skills
    assert "redis" in job.preferred_skills


def test_truthfulness_guardrail_does_not_claim_missing_skill(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'resume.db'}"
    init_db(database_url)
    service = TailoredResumeService(
        bundle(),
        DiscoveryQueueRepository(database_url),
        ApplicationRepository(database_url),
        ResumeVersionRepository(database_url),
    )
    job = parsed_job("Required: Kubernetes and Redis. Build backend systems.")

    response = service.generate_tailored(ResumeGenerateTailoredRequest(job=job))

    assert "kubernetes" in response.ats.missing_keywords
    assert "Kubernetes" not in response.resume_markdown


def test_resume_version_creation_from_queue_job(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'resume.db'}"
    init_db(database_url)
    queue_repo = DiscoveryQueueRepository(database_url)
    saved = queue_repo.save_discovered_job(
        DiscoveredJobSaveRequest(
            title="AI Engineer",
            company="Acme AI",
            job_url="https://example.com/job",
            source="manual",
            location="Remote",
            description="Required: Python, FastAPI, React, OpenAI.",
            required_skills=["python", "fastapi", "react", "openai"],
        )
    ).job
    version_repo = ResumeVersionRepository(database_url)
    service = TailoredResumeService(bundle(), queue_repo, ApplicationRepository(database_url), version_repo)

    response = service.generate_tailored(ResumeGenerateTailoredRequest(job_queue_id=saved.id))

    assert response.version_record.job_queue_id == saved.id
    assert response.version_record.ats_score == response.ats.ats_score
    assert response.docx_path is not None
    assert response.version_record.file_path_docx == response.docx_path
    assert version_repo.get(response.version_record.id).resume_version_id == response.resume_version


def test_resume_version_status_update_select_uniqueness_and_archive(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'resume.db'}"
    init_db(database_url)
    repo = ResumeVersionRepository(database_url)
    first = repo.create(
        resume_version_id="v1",
        job_queue_id=1,
        application_id=None,
        title="AI Engineer",
        company="Acme",
        ats_score=80,
        matched_keywords=["python"],
        missing_keywords=[],
        file_path="one.pdf",
        file_path_docx="one.docx",
    )
    second = repo.create(
        resume_version_id="v2",
        job_queue_id=1,
        application_id=None,
        title="AI Engineer",
        company="Acme",
        ats_score=85,
        matched_keywords=["python"],
        missing_keywords=[],
        file_path="two.pdf",
        file_path_docx="two.docx",
    )

    reviewed = repo.update_status(first.id, ResumeVersionStatus.REVIEWED)
    assert reviewed.status == ResumeVersionStatus.REVIEWED
    selected = repo.select(second.id)
    assert selected.status == ResumeVersionStatus.SELECTED
    assert repo.get(first.id).status == ResumeVersionStatus.REVIEWED
    archived = repo.archive(second.id)
    assert archived.status == ResumeVersionStatus.ARCHIVED


def test_gap_action_plan_and_safe_phrasing_do_not_invent_missing_skills() -> None:
    analyzer = ATSAnalyzer(bundle())

    items = analyzer.gap_action_plan(["docker"])
    safe_phrasing = analyzer._safe_phrasing_suggestions(items)

    assert items[0].skill == "docker"
    assert "Do not add docker as a skill unless it is true." in items[0].safe_resume_action
    assert "exposure to related tooling" in safe_phrasing[0]


def test_ats_and_tailored_resume_routes(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'routes.db'}"
    init_db(database_url)
    queue_repo = DiscoveryQueueRepository(database_url)
    application_repo = ApplicationRepository(database_url)
    resume_repo = ResumeVersionRepository(database_url)
    app.dependency_overrides[get_discovery_queue_repository] = lambda: queue_repo
    app.dependency_overrides[get_application_repository] = lambda: application_repo
    app.dependency_overrides[get_resume_version_repository] = lambda: resume_repo
    client = TestClient(app)

    try:
        job_payload = {
            "title": "AI Engineer",
            "company": "Acme AI",
            "description": "Required: Python, FastAPI, React, OpenAI.",
            "source": "manual",
        }
        analyze = client.post("/jobs/analyze", json=job_payload)
        job = analyze.json()["job"]
        ats = client.post("/ats/analyze", json={"job": job})
        assert ats.status_code == 200
        assert ats.json()["ats_score"] >= 60

        generated = client.post("/resumes/generate-tailored", json={"job": job})
        assert generated.status_code == 200
        version_id = generated.json()["version_record"]["id"]

        versions = client.get("/resumes/versions")
        assert versions.status_code == 200
        assert len(versions.json()["versions"]) == 1

        detail = client.get(f"/resumes/versions/{version_id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == version_id

        reviewed = client.patch(f"/resumes/versions/{version_id}/status", json={"status": "reviewed"})
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "reviewed"

        selected = client.post(f"/resumes/versions/{version_id}/select")
        assert selected.status_code == 200
        assert selected.json()["status"] == "selected"

        gap_plan = client.post("/ats/gap-action-plan", json={"missing_keywords": ["docker"]})
        assert gap_plan.status_code == 200
        assert gap_plan.json()["items"][0]["skill"] == "docker"
    finally:
        app.dependency_overrides.clear()
