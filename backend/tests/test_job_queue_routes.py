from fastapi.testclient import TestClient

from app.api.routes import get_application_repository, get_discovery_queue_repository
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.db.sqlite import init_db
from app.main import app


def test_job_discover_and_queue_routes_with_manual_source(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'routes.db'}"
    init_db(database_url)
    queue_repository = DiscoveryQueueRepository(database_url)
    application_repository = ApplicationRepository(database_url)
    app.dependency_overrides[get_discovery_queue_repository] = lambda: queue_repository
    app.dependency_overrides[get_application_repository] = lambda: application_repository
    client = TestClient(app)

    try:
        discover = client.post(
            "/jobs/discover",
            json={
                "query": "AI Engineer",
                "location": "Remote",
                "sources": ["manual"],
                "manual_urls": ["https://example.com/apply"],
                "limit": 5,
            },
        )
        assert discover.status_code == 200
        body = discover.json()
        assert body["inserted_count"] == 1
        assert body["duplicate_count"] == 0
        job_id = body["jobs"][0]["id"]

        queue = client.get("/jobs/queue")
        assert queue.status_code == 200
        assert len(queue.json()["jobs"]) == 1
        filtered = client.get("/jobs/queue", params={"source": "manual", "search": "Manual", "min_fit_score": 0})
        assert filtered.status_code == 200
        assert len(filtered.json()["jobs"]) == 1

        status = client.patch(f"/jobs/queue/{job_id}/status", json={"queue_status": "shortlisted"})
        assert status.status_code == 200
        assert status.json()["queue_status"] == "shortlisted"

        skipped = client.post(f"/jobs/queue/{job_id}/skip")
        assert skipped.status_code == 200
        assert skipped.json()["queue_status"] == "skipped"

        shortlisted = client.post(f"/jobs/queue/{job_id}/shortlist")
        assert shortlisted.status_code == 200
        assert shortlisted.json()["queue_status"] == "shortlisted"

        converted = client.post(f"/jobs/queue/{job_id}/convert-to-application")
        assert converted.status_code == 200
        assert converted.json()["queue_status"] == "applied"

        daily = client.get("/dashboard/daily-target")
        assert daily.status_code == 200
        daily_body = daily.json()
        assert {
            "daily_target",
            "applied_today",
            "remaining_today",
            "discovered_today",
            "shortlisted_today",
            "skipped_today",
        } <= daily_body.keys()
        assert daily_body["applied_today"] == 1

        applications = client.get("/applications")
        assert len(applications.json()["applications"]) == 1
    finally:
        app.dependency_overrides.clear()
