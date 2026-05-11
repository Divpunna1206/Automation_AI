from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.api.routes import get_outreach_repository, get_outreach_service
from app.core.config_loader import Answers, Preferences, Profile, ProfileBundle
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.outreach_repository import OutreachRepository
from app.db.repository import ApplicationRepository
from app.db.sqlite import init_db
from app.main import app
from app.models.outreach import (
    OutreachChannel,
    OutreachContactCreate,
    OutreachContactUpdate,
    OutreachFollowUpMessageRequest,
    OutreachMessageGenerateRequest,
    OutreachRecordCreate,
    OutreachRecordStatusUpdate,
    OutreachStatus,
    OutreachSearchSuggestionRequest,
)
from app.services.outreach import OutreachService


def bundle() -> ProfileBundle:
    return ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            location="Remote",
            linkedin="https://linkedin.com/in/test",
            github="https://github.com/test",
            summary="Full-stack AI engineer focused on local automation.",
            skills=["Python", "FastAPI", "React", "Playwright", "SQLite"],
        ),
        preferences=Preferences(target_titles=["AI Engineer"]),
        answers=Answers(),
    )


def outreach_service(database_url: str) -> OutreachService:
    return OutreachService(
        bundle(),
        DiscoveryQueueRepository(database_url),
        ApplicationRepository(database_url),
    )


def test_contact_creation_list_update_archive(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach.db'}"
    init_db(database_url)
    repo = OutreachRepository(database_url)

    contact = repo.create_contact(
        OutreachContactCreate(company="Acme AI", name="Asha", title="Recruiter", linkedin_url="https://linkedin.com/in/asha")
    )
    assert contact.id
    assert contact.company == "Acme AI"
    assert repo.list_contacts(company="Acme AI").contacts[0].name == "Asha"

    updated = repo.update_contact(contact.id, OutreachContactUpdate(email="asha@example.com", confidence_score=0.8))
    assert updated.email == "asha@example.com"
    assert updated.confidence_score == 0.8

    archived = repo.archive_contact(contact.id)
    assert archived.archived is True
    assert repo.list_contacts(company="Acme AI").contacts == []
    assert repo.list_contacts(company="Acme AI", include_archived=True).contacts[0].archived is True


def test_search_suggestions_and_low_confidence_email_guesses(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach.db'}"
    init_db(database_url)
    service = outreach_service(database_url)

    response = service.search_suggestions(
        OutreachSearchSuggestionRequest(
            company="Acme AI",
            role_title="AI Engineer",
            job_url="https://careers.acme.ai/jobs/123",
        )
    )

    assert 'site:linkedin.com/in "Acme AI" recruiter' in response.search_queries
    assert 'site:linkedin.com/in "Acme AI" talent acquisition' in response.search_queries
    assert 'site:linkedin.com/in "Acme AI" hiring manager "AI Engineer"' in response.search_queries
    assert response.company_domain == "acme.ai"
    assert {guess.example for guess in response.guessed_email_patterns} == {
        "firstname.lastname@acme.ai",
        "first@acme.ai",
        "firstlast@acme.ai",
    }
    assert all(guess.confidence_score <= 0.2 for guess in response.guessed_email_patterns)
    assert all("verify manually" in guess.warning.lower() for guess in response.guessed_email_patterns)


def test_message_generation_uses_profile_without_fabricated_claims(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach.db'}"
    init_db(database_url)
    service = outreach_service(database_url)

    response = service.generate_message(
        OutreachMessageGenerateRequest(
            company="Acme AI",
            role_title="AI Engineer",
            contact_name="Asha",
            channel=OutreachChannel.LINKEDIN,
        )
    )

    message = response.message_text.lower()
    assert "acme ai" in message
    assert "ai engineer" in message
    assert "python" in message or "fastapi" in message
    assert "referral" not in message
    assert "interview" not in message


def test_outreach_record_creation_status_update_and_follow_up_date(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach.db'}"
    init_db(database_url)
    repo = OutreachRepository(database_url)
    contact = repo.create_contact(OutreachContactCreate(company="Acme AI", name="Asha"))

    record = repo.create_record(
        OutreachRecordCreate(
            contact_id=contact.id,
            channel=OutreachChannel.EMAIL,
            message_text="Manual draft only.",
        )
    )

    assert record.status == OutreachStatus.DRAFTED
    assert record.follow_up_date is not None
    assert record.follow_up_date >= date.today() + timedelta(days=5)

    updated = repo.update_record_status(record.id, OutreachRecordStatusUpdate(status=OutreachStatus.SENT_MANUALLY))
    assert updated.status == OutreachStatus.SENT_MANUALLY


def test_outreach_dashboard_and_follow_up_filters(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach_dashboard.db'}"
    init_db(database_url)
    repo = OutreachRepository(database_url)
    contact = repo.create_contact(OutreachContactCreate(company="Acme AI", name="Asha"))

    today = date.today()
    repo.create_record(
        OutreachRecordCreate(
            contact_id=contact.id,
            channel=OutreachChannel.EMAIL,
            message_text="Due today.",
            status=OutreachStatus.SENT_MANUALLY,
            follow_up_date=today,
        )
    )
    repo.create_record(
        OutreachRecordCreate(
            contact_id=contact.id,
            channel=OutreachChannel.LINKEDIN,
            message_text="Overdue.",
            status=OutreachStatus.NO_RESPONSE,
            follow_up_date=today - timedelta(days=2),
        )
    )
    repo.create_record(
        OutreachRecordCreate(
            contact_id=contact.id,
            channel=OutreachChannel.LINKEDIN,
            message_text="Upcoming.",
            status=OutreachStatus.DRAFTED,
            follow_up_date=today + timedelta(days=3),
        )
    )
    repo.create_record(
        OutreachRecordCreate(
            contact_id=contact.id,
            channel=OutreachChannel.EMAIL,
            message_text="Replied.",
            status=OutreachStatus.REPLIED,
            follow_up_date=today,
        )
    )

    dashboard = repo.dashboard()
    assert dashboard.drafted == 1
    assert dashboard.sent_manually == 1
    assert dashboard.replies == 1
    assert dashboard.no_response == 1
    assert dashboard.follow_ups_due_today == 1
    assert dashboard.overdue_follow_ups == 1
    assert dashboard.upcoming_follow_ups == 1

    assert len(repo.follow_ups(due_today=True).records) == 1
    assert len(repo.follow_ups(overdue=True).records) == 1
    assert len(repo.follow_ups(upcoming=True).records) == 1
    assert len(repo.follow_ups(company="Acme AI", channel=OutreachChannel.LINKEDIN).records) == 2


def test_message_history_by_contact_and_company(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach_history.db'}"
    init_db(database_url)
    repo = OutreachRepository(database_url)
    acme_contact = repo.create_contact(OutreachContactCreate(company="Acme AI", name="Asha"))
    other_contact = repo.create_contact(OutreachContactCreate(company="Other Co", name="Ravi"))
    first = repo.create_record(
        OutreachRecordCreate(contact_id=acme_contact.id, channel=OutreachChannel.EMAIL, message_text="First")
    )
    second = repo.create_record(
        OutreachRecordCreate(contact_id=acme_contact.id, channel=OutreachChannel.LINKEDIN, message_text="Second")
    )
    repo.create_record(
        OutreachRecordCreate(contact_id=other_contact.id, channel=OutreachChannel.EMAIL, message_text="Other")
    )

    by_contact = repo.history(contact_id=acme_contact.id).records
    assert [record.id for record in by_contact] == [second.id, first.id]
    assert all(record.company == "Acme AI" for record in by_contact)

    by_company = repo.history(company="Acme AI").records
    assert len(by_company) == 2
    assert {record.contact_name for record in by_company} == {"Asha"}


def test_follow_up_message_generation_is_safe(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach_followup.db'}"
    init_db(database_url)
    service = outreach_service(database_url)

    response = service.generate_follow_up(
        OutreachFollowUpMessageRequest(
            original_message="I applied with verified Python and FastAPI experience.",
            company="Acme AI",
            role_title="AI Engineer",
            days_since_first_message=7,
            channel=OutreachChannel.LINKEDIN,
            contact_name="Asha",
        )
    )

    message = response.message_text.lower()
    assert "acme ai" in message
    assert "ai engineer" in message
    assert "just checking in" not in message
    assert "desperate" not in message
    assert "referral" not in message
    assert "interview" not in message


def test_outreach_api_routes(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outreach_routes.db'}"
    init_db(database_url)
    repo = OutreachRepository(database_url)
    service = outreach_service(database_url)
    app.dependency_overrides[get_outreach_repository] = lambda: repo
    app.dependency_overrides[get_outreach_service] = lambda: service
    client = TestClient(app)

    try:
        created = client.post("/outreach/contacts", json={"company": "Acme AI", "name": "Asha", "title": "Recruiter"})
        assert created.status_code == 200
        contact_id = created.json()["id"]

        listed = client.get("/outreach/contacts", params={"company": "Acme AI"})
        assert listed.status_code == 200
        assert len(listed.json()["contacts"]) == 1

        updated = client.patch(f"/outreach/contacts/{contact_id}", json={"email": "asha@example.com"})
        assert updated.status_code == 200
        assert updated.json()["email"] == "asha@example.com"

        suggestions = client.post(
            "/outreach/search-suggestions",
            json={"company": "Acme AI", "role_title": "AI Engineer", "job_url": "https://careers.acme.ai/job"},
        )
        assert suggestions.status_code == 200
        assert suggestions.json()["guessed_email_patterns"][0]["confidence_score"] <= 0.2

        message = client.post(
            "/outreach/messages/generate",
            json={"company": "Acme AI", "role_title": "AI Engineer", "contact_name": "Asha", "channel": "email"},
        )
        assert message.status_code == 200
        message_text = message.json()["message_text"].lower()
        assert "referral" not in message_text
        assert "interview" not in message_text

        record = client.post(
            "/outreach/records",
            json={"contact_id": contact_id, "channel": "linkedin", "message_text": message.json()["message_text"]},
        )
        assert record.status_code == 200
        record_id = record.json()["id"]
        assert record.json()["follow_up_date"] is not None

        status = client.patch(f"/outreach/records/{record_id}/status", json={"status": "sent_manually"})
        assert status.status_code == 200
        assert status.json()["status"] == "sent_manually"

        dashboard = client.get("/outreach/dashboard")
        assert dashboard.status_code == 200
        assert {"drafted", "sent_manually", "replies", "no_response", "follow_ups_due_today"} <= dashboard.json().keys()

        follow_ups = client.get("/outreach/follow-ups", params={"upcoming": True, "company": "Acme AI"})
        assert follow_ups.status_code == 200
        assert len(follow_ups.json()["records"]) == 1

        history = client.get("/outreach/history", params={"contact_id": contact_id})
        assert history.status_code == 200
        assert len(history.json()["records"]) == 1

        follow_up = client.post(
            "/outreach/messages/follow-up",
            json={
                "original_message": message.json()["message_text"],
                "company": "Acme AI",
                "role_title": "AI Engineer",
                "days_since_first_message": 6,
                "channel": "email",
                "contact_name": "Asha",
            },
        )
        assert follow_up.status_code == 200
        assert "just checking in" not in follow_up.json()["message_text"].lower()

        archived = client.patch(f"/outreach/contacts/{contact_id}", json={"archived": True})
        assert archived.status_code == 200
        assert archived.json()["archived"] is True

        assert client.post("/outreach/send", json={}).status_code == 404
        assert client.post("/outreach/messages/send", json={}).status_code == 404
    finally:
        app.dependency_overrides.clear()
