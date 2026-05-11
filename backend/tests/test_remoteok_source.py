import httpx

from app.core.config_loader import Answers, Preferences, Profile, ProfileBundle
from app.core.settings import Settings
from app.models.job import JobSearchRequest
from app.services.fit_scorer import FitScorer
from app.services.job_discovery import JobDiscoveryService


def bundle() -> ProfileBundle:
    return ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            summary="AI engineer",
            skills=["Python", "FastAPI", "React"],
        ),
        preferences=Preferences(target_titles=["AI Engineer"], target_locations=["Remote"]),
        answers=Answers(),
    )


def test_remoteok_success_mocked(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json=[
                {"legal": "ok"},
                {
                    "position": "AI Engineer",
                    "company": "Acme AI",
                    "description": "Build FastAPI and React AI systems.",
                    "url": "https://remoteok.com/remote-jobs/1",
                    "location": "Remote",
                    "tags": ["python", "fastapi"],
                },
            ],
            request=httpx.Request("GET", args[0]),
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    service = JobDiscoveryService(Settings(), FitScorer(bundle()))

    response = service.search(JobSearchRequest(query="AI Engineer", sources=["remoteok"], limit=5))

    assert len(response.results) == 1
    assert response.results[0].listing.source == "remoteok"
    assert response.source_errors == {}


def test_remoteok_network_failure_is_reported(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", fake_get)
    service = JobDiscoveryService(Settings(), FitScorer(bundle()))

    response = service.search(JobSearchRequest(query="AI Engineer", sources=["remoteok"], limit=5))

    assert response.results == []
    assert "RemoteOK request failed" in response.source_errors["remoteok"]


def test_remoteok_malformed_response_is_reported(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return httpx.Response(200, json={"unexpected": "shape"}, request=httpx.Request("GET", args[0]))

    monkeypatch.setattr(httpx, "get", fake_get)
    service = JobDiscoveryService(Settings(), FitScorer(bundle()))

    response = service.search(JobSearchRequest(query="AI Engineer", sources=["remoteok"], limit=5))

    assert response.results == []
    assert "unexpected response shape" in response.source_errors["remoteok"]
