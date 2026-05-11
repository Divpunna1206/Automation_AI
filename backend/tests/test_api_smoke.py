from fastapi.testclient import TestClient

from app.db.repository import ApplicationRepository
from app.db.repository import get_application_repository
from app.db.sqlite import init_db
from app.main import app


def test_core_api_smoke_with_real_sample_config(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'smoke.db'}"
    init_db(database_url)
    repository = ApplicationRepository(database_url)
    app.dependency_overrides[get_application_repository] = lambda: repository
    client = TestClient(app)

    try:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        analyze = client.post(
            "/jobs/analyze",
            json={
                "title": "Senior Full-Stack AI Engineer",
                "company": "Acme AI",
                "description": "Build FastAPI, React, SQL, Playwright, and LLM workflows.",
                "url": "https://example.com/jobs/123?utm_source=test",
                "location": "Remote",
                "source": "manual",
            },
        )
        assert analyze.status_code == 200
        job = analyze.json()["job"]
        assert "fastapi" in job["required_skills"]

        score = client.post("/jobs/score", json={"job": job})
        assert score.status_code == 200
        fit_score = score.json()["score"]
        assert fit_score["score"] >= 0

        resume = client.post("/resumes/generate", json={"job": job, "fit_score": fit_score})
        assert resume.status_code == 200
        resume_body = resume.json()
        assert resume_body["resume_version"]
        assert resume_body["resume_markdown"]

        cover = client.post(
            "/cover-letter/generate",
            json={"job": job, "resume_version": resume_body["resume_version"]},
        )
        assert cover.status_code == 200
        cover_letter = cover.json()["cover_letter"]
        assert "Acme AI" in cover_letter

        save = client.post(
            "/applications",
            json={
                "company": job["company"],
                "title": job["title"],
                "job_url": job["url"],
                "source": job["source"],
                "fit_score": fit_score["score"],
                "recommendation": fit_score["recommendation"],
                "resume_version": resume_body["resume_version"],
                "resume_markdown": resume_body["resume_markdown"],
                "resume_pdf_path": resume_body["pdf_path"],
                "cover_letter": cover_letter,
                "status": "materials_generated",
                "follow_up_date": "2026-05-10",
                "notes": "Smoke test application.",
            },
        )
        assert save.status_code == 200
        application = save.json()["application"]
        application_id = application["id"]
        assert application["title"] == job["title"]
        assert application["company"] == job["company"]
        assert application["job_url"] == "https://example.com/jobs/123?utm_source=test"
        assert application["source"] == "manual"
        assert application["fit_score"] == fit_score["score"]
        assert application["status"] == "materials_generated"
        assert application["resume_version"] == resume_body["resume_version"]
        assert application["cover_letter"] == cover_letter
        assert application["follow_up_date"] == "2026-05-10"
        assert application["notes"] == "Smoke test application."

        applications = client.get("/applications")
        assert applications.status_code == 200
        assert len(applications.json()["applications"]) == 1

        stats = client.get("/dashboard/stats")
        assert stats.status_code == 200
        assert stats.json()["total_jobs"] == 1

        status = client.patch(f"/applications/{application_id}/status", json={"status": "approved"})
        assert status.status_code == 200
        assert status.json()["application"]["status"] == "approved"

        fill_plan = client.post(
            "/forms/fill-plan",
            json={
                "application_url": job["url"],
                "resume_path": resume_body["pdf_path"],
                "cover_letter": cover_letter,
                "dry_run": True,
            },
        )
        assert fill_plan.status_code == 200
        assert fill_plan.json()["requires_user_approval"] is True
        assert fill_plan.json()["can_submit"] is False
    finally:
        app.dependency_overrides.clear()
