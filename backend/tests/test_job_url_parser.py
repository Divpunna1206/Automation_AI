import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.job_url_parser import JobURLParser


def test_parse_url_invalid_url_route() -> None:
    client = TestClient(app)

    response = client.post("/jobs/parse-url", json={"job_url": "not-a-url"})

    assert response.status_code == 422


def test_parse_url_rejects_guarded_domains() -> None:
    client = TestClient(app)

    response = client.post("/jobs/parse-url", json={"job_url": "https://www.linkedin.com/jobs/view/123"})

    assert response.status_code == 400
    assert "Paste the job description manually" in response.json()["detail"]


def test_parse_url_empty_content(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            text="<html><title>Empty</title><body>Too short</body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", args[0]),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(ValueError, match="did not contain enough readable job text"):
        JobURLParser().parse("https://example.com/jobs/123")


def test_parse_url_success(monkeypatch) -> None:
    html = """
    <html>
      <title>AI Engineer - Acme AI</title>
      <body>
        <main>
          Location: Remote India.
          We are hiring an AI Engineer to build FastAPI, React, SQL, and LLM systems.
          This role collaborates with product and engineering teams on human-in-the-loop workflows.
          You will design services, improve automation, and review generated outputs.
        </main>
      </body>
    </html>
    """

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=html, headers={"content-type": "text/html"}, request=httpx.Request("GET", args[0]))

    monkeypatch.setattr(httpx, "get", fake_get)

    response = JobURLParser().parse("https://careers.example.com/jobs/123")

    assert response.title == "AI Engineer"
    assert response.company == "Acme AI"
    assert response.source == "careers"
    assert response.location == "Remote"
    assert "FastAPI" in response.description
