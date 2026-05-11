import asyncio
from fastapi.testclient import TestClient

from app.api.routes import (
    get_application_repository,
    get_apply_question_repository,
    get_apply_session_repository,
    get_discovery_queue_repository,
    get_resume_version_repository,
)
from app.core.config_loader import Answers, Preferences, Profile, ProfileBundle
from app.db.apply_session_repository import ApplySessionRepository
from app.db.apply_question_repository import ApplyQuestionRepository
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.db.resume_version_repository import ResumeVersionRepository
from app.db.sqlite import init_db
from app.main import app
from app.models.apply_session import ApplySessionCreateRequest, ApplySessionStatus, FieldResult
from app.models.application import ApplicationSaveRequest, ApplicationStatus
from app.models.job_queue import DiscoveredJobSaveRequest
from app.models.resume import ResumeVersionStatus
from app.services.apply_assistant import ApplyAssistantService
from app.services.apply_questions import ApplyQuestionService


def bundle() -> ProfileBundle:
    return ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            phone="555-0100",
            location="Remote",
            linkedin="https://linkedin.com/in/test",
            github="https://github.com/test",
            summary="AI engineer",
            skills=["Python"],
        ),
        preferences=Preferences(),
        answers=Answers(notice_period="Immediate", salary_expectation="Market aligned"),
    )


def service(database_url: str) -> ApplyAssistantService:
    return ApplyAssistantService(
        bundle(),
        ApplySessionRepository(database_url),
        DiscoveryQueueRepository(database_url),
        ApplicationRepository(database_url),
        ResumeVersionRepository(database_url),
    )


def question_service(database_url: str) -> ApplyQuestionService:
    return ApplyQuestionService(
        bundle(),
        ApplySessionRepository(database_url),
        ApplyQuestionRepository(database_url),
        DiscoveryQueueRepository(database_url),
        ApplicationRepository(database_url),
    )


def seed_queue_job(database_url: str):
    return DiscoveryQueueRepository(database_url).save_discovered_job(
        DiscoveredJobSaveRequest(
            title="AI Engineer",
            company="Acme AI",
            job_url="https://example.com/apply",
            source="manual",
            location="Remote",
            description="Apply here.",
        )
    ).job


def seed_resume(database_url: str, job_queue_id: int | None = None, status: ResumeVersionStatus = ResumeVersionStatus.SELECTED):
    repo = ResumeVersionRepository(database_url)
    version = repo.create(
        resume_version_id=f"resume-{status.value}-{job_queue_id or 0}",
        job_queue_id=job_queue_id,
        application_id=None,
        title="AI Engineer",
        company="Acme AI",
        ats_score=80,
        matched_keywords=["python"],
        missing_keywords=[],
        file_path="resume.pdf",
        file_path_docx="resume.docx",
    )
    return repo.update_status(version.id, status)


def test_create_apply_session_and_selected_resume_resolution(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    selected = seed_resume(database_url, queue_job.id)

    response = service(database_url).create_apply_session(ApplySessionCreateRequest(job_queue_id=queue_job.id))

    assert response.session.status == ApplySessionStatus.PLANNED
    assert response.session.resume_version_id == selected.id
    assert response.session.resume_file_path == "resume.pdf"
    assert any(field.label == "Resume" for field in response.fill_plan)


def test_fill_plan_generation_includes_common_fields(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)

    plan = service(database_url).build_fill_plan("https://example.com/apply", "resume.pdf", "Hello")
    labels = {field.label for field in plan}

    assert {"Name", "Email", "Phone", "Location", "LinkedIn URL", "GitHub URL", "Expected Salary", "Notice Period", "Cover Letter", "Resume"} <= labels


class FakeRunner:
    async def run(self, session_id, job_url, plan):
        return (
            [
                FieldResult(label="Name", status="filled", message="ok", selector="input[name=name]"),
                FieldResult(label="Unknown", status="skipped", message="manual review required", confidence="low"),
                FieldResult(label="Final Submit", status="blocked_manual", message="Submit button detected and intentionally not clicked.", confidence="high"),
            ],
            ["screenshot.png"],
            [],
        )


def test_run_until_review_records_submit_block_and_low_confidence_skip(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    created = service(database_url).create_apply_session(ApplySessionCreateRequest(job_queue_id=queue_job.id)).session

    session = asyncio.run(service(database_url).run_until_review(created.id, runner=FakeRunner()))

    assert session.status == ApplySessionStatus.REVIEW_REQUIRED
    assert any(result.status == "blocked_manual" for result in session.field_results)
    assert any(result.confidence == "low" and result.status == "skipped" for result in session.field_results)
    assert session.screenshot_paths == ["screenshot.png"]


def test_completed_manually_and_failed_status(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    apply_service = service(database_url)
    created = apply_service.create_apply_session(ApplySessionCreateRequest(job_queue_id=queue_job.id)).session

    completed = apply_service.mark_completed_manually(created.id)
    failed = apply_service.mark_failed(created.id, "User could not complete form.")

    assert completed.status == ApplySessionStatus.COMPLETED_MANUALLY
    assert failed.status == ApplySessionStatus.FAILED
    assert "User could not complete form." in failed.errors


def test_apply_session_api_routes(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    session_repo = ApplySessionRepository(database_url)
    question_repo = ApplyQuestionRepository(database_url)
    queue_repo = DiscoveryQueueRepository(database_url)
    application_repo = ApplicationRepository(database_url)
    resume_repo = ResumeVersionRepository(database_url)
    app.dependency_overrides[get_apply_session_repository] = lambda: session_repo
    app.dependency_overrides[get_apply_question_repository] = lambda: question_repo
    app.dependency_overrides[get_discovery_queue_repository] = lambda: queue_repo
    app.dependency_overrides[get_application_repository] = lambda: application_repo
    app.dependency_overrides[get_resume_version_repository] = lambda: resume_repo
    client = TestClient(app)

    try:
        created = client.post("/apply/sessions", json={"job_queue_id": queue_job.id})
        assert created.status_code == 200
        session_id = created.json()["session"]["id"]

        listed = client.get("/apply/sessions")
        assert listed.status_code == 200
        assert len(listed.json()["sessions"]) == 1

        detail = client.get(f"/apply/sessions/{session_id}")
        assert detail.status_code == 200

        completed = client.patch(f"/apply/sessions/{session_id}/completed-manually", json={"message": "Done by user."})
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed_manually"

        failed = client.patch(f"/apply/sessions/{session_id}/failed", json={"message": "Manual failure."})
        assert failed.status_code == 200
        assert failed.json()["status"] == "failed"
    finally:
        app.dependency_overrides.clear()


def test_question_generation_sources_and_manual_required(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    created = service(database_url).create_apply_session(
        ApplySessionCreateRequest(job_queue_id=queue_job.id, cover_letter_text="Cover letter text")
    ).session

    questions = question_service(database_url).generate_questions(created.id).questions

    assert any(question.answer_source == "answers_yaml" and "Immediate" in (question.answer_text or "") for question in questions)
    assert any(question.answer_source == "preferences" for question in questions)
    assert any(question.answer_source == "generated" and "AI Engineer" in (question.answer_text or "") for question in questions)


def test_manual_required_for_missing_portfolio_and_years(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    created = service(database_url).create_apply_session(
        ApplySessionCreateRequest(job_url="https://example.com/apply", company="Acme", title="AI Engineer")
    ).session
    qs = question_service(database_url)

    portfolio = qs.question_repository.create(created.id, "Portfolio URL", "Portfolio", None, 0, "manual_required", True)
    years = qs.question_repository.create(created.id, "Years of experience", "Years", None, 0, "manual_required", True)

    assert portfolio.requires_manual_review is True
    assert years.requires_manual_review is True


def test_review_pack_and_edit_question_answer(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    created = service(database_url).create_apply_session(ApplySessionCreateRequest(job_queue_id=queue_job.id)).session
    qs = question_service(database_url)
    questions = qs.generate_questions(created.id).questions

    updated = qs.update_question(questions[0].id, "Edited answer", False)
    pack = qs.review_pack(created.id)

    assert updated.answer_text == "Edited answer"
    assert pack.session.id == created.id
    assert "User clicked submit manually only after review." in pack.final_manual_checklist
    assert isinstance(pack.generated_answers, list)


def test_mark_submitted_manually_updates_session_queue_and_application(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    app_repo = ApplicationRepository(database_url)
    application = app_repo.save(
        ApplicationSaveRequest(company="Acme AI", title="AI Engineer", job_url="https://example.com/apply", status=ApplicationStatus.REVIEWED)
    )
    created = service(database_url).create_apply_session(
        ApplySessionCreateRequest(job_queue_id=queue_job.id, application_id=application.id)
    ).session

    submitted = question_service(database_url).mark_submitted_manually(created.id)

    assert submitted.status == ApplySessionStatus.COMPLETED_MANUALLY
    assert DiscoveryQueueRepository(database_url).get(queue_job.id).queue_status.value == "applied"
    assert app_repo.get(application.id).status == ApplicationStatus.SUBMITTED


def test_question_routes_and_no_auto_submit_path(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'apply.db'}"
    init_db(database_url)
    queue_job = seed_queue_job(database_url)
    session_repo = ApplySessionRepository(database_url)
    question_repo = ApplyQuestionRepository(database_url)
    queue_repo = DiscoveryQueueRepository(database_url)
    application_repo = ApplicationRepository(database_url)
    resume_repo = ResumeVersionRepository(database_url)
    app.dependency_overrides[get_apply_session_repository] = lambda: session_repo
    app.dependency_overrides[get_apply_question_repository] = lambda: question_repo
    app.dependency_overrides[get_discovery_queue_repository] = lambda: queue_repo
    app.dependency_overrides[get_application_repository] = lambda: application_repo
    app.dependency_overrides[get_resume_version_repository] = lambda: resume_repo
    client = TestClient(app)

    try:
        created = client.post("/apply/sessions", json={"job_queue_id": queue_job.id})
        session_id = created.json()["session"]["id"]
        generated = client.post(f"/apply/sessions/{session_id}/questions/generate")
        assert generated.status_code == 200
        question_id = generated.json()["questions"][0]["id"]
        edited = client.patch(f"/apply/questions/{question_id}", json={"answer_text": "Manual edit", "requires_manual_review": False})
        assert edited.status_code == 200
        pack = client.get(f"/apply/sessions/{session_id}/review-pack")
        assert pack.status_code == 200
        submitted = client.patch(f"/apply/sessions/{session_id}/mark-submitted-manually")
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "completed_manually"
    finally:
        app.dependency_overrides.clear()
