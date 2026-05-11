from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import get_system_service
from app.core.settings import Settings
from app.db.sqlite import get_connection, init_db
from app.main import app
from app.services.system import SystemService


def test_system_health_check(tmp_path) -> None:
    settings = make_settings(tmp_path)
    init_db(settings.database_url)
    response = SystemService(settings).health_check()

    assert response.backend_status == "ok"
    assert response.database_reachable is True
    assert response.config_valid is True
    assert response.artifacts_writable is True
    assert response.frontend_api_base_url_suggestion == "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000"
    assert response.llm_status in {"local fallback active", "openai-compatible configured", "openai key missing"}


def test_seed_demo_data_creates_local_records(tmp_path) -> None:
    settings = make_settings(tmp_path)
    service = SystemService(settings)

    response = service.seed_demo_data()

    assert response.created_jobs >= 3
    assert response.created_applications == 2
    assert response.created_resume_versions == 2
    assert response.created_contacts == 2
    assert response.created_outreach_records == 2

    with get_connection(settings.database_url) as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM discovered_jobs").fetchone()["count"] >= 3
        assert connection.execute("SELECT COUNT(*) AS count FROM applications").fetchone()["count"] == 2
        assert connection.execute("SELECT COUNT(*) AS count FROM resume_versions").fetchone()["count"] == 2
        assert connection.execute("SELECT COUNT(*) AS count FROM outreach_contacts").fetchone()["count"] == 2
        assert connection.execute("SELECT COUNT(*) AS count FROM outreach_records").fetchone()["count"] == 2


def test_system_routes(tmp_path) -> None:
    settings = make_settings(tmp_path)
    service = SystemService(settings)
    app.dependency_overrides[get_system_service] = lambda: service
    client = TestClient(app)

    try:
        health = client.get("/system/health-check")
        assert health.status_code == 200
        assert health.json()["database_reachable"] is True

        seed = client.post("/system/seed-demo-data")
        assert seed.status_code == 200
        assert seed.json()["created_applications"] == 2
    finally:
        app.dependency_overrides.clear()


def test_smoke_script_endpoint_list_is_current() -> None:
    script = Path("scripts/smoke_test.py").read_text(encoding="utf-8")
    for endpoint in (
        "/health",
        "/system/health-check",
        "/jobs/queue",
        "/dashboard/daily-target",
        "/analytics/overview",
        "/outreach/dashboard",
    ):
        assert endpoint in script


def make_settings(tmp_path) -> Settings:
    profile = tmp_path / "profile.yaml"
    preferences = tmp_path / "preferences.yaml"
    answers = tmp_path / "answers.yaml"
    profile.write_text(
        """
name: Demo User
email: demo@example.com
summary: Local job hunt tester.
skills:
  - Python
  - FastAPI
experience: []
education: []
certifications: []
""".strip(),
        encoding="utf-8",
    )
    preferences.write_text("daily_application_target: 5\n", encoding="utf-8")
    answers.write_text("{}\n", encoding="utf-8")
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'system.db'}",
        profile_path=profile,
        preferences_path=preferences,
        answers_path=answers,
        artifacts_dir=tmp_path / "artifacts",
        llm_provider="local",
    )
