from app.automation.form_filler import PlaywrightFormFiller
from app.core.config_loader import Answers, Preferences, Profile, ProfileBundle


def test_form_fill_plan_requires_approval_and_never_submit() -> None:
    bundle = ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            phone="555-0100",
            linkedin="https://linkedin.com/in/test",
            summary="Applied AI developer",
            skills=["Python"],
        ),
        preferences=Preferences(),
        answers=Answers(),
    )

    plan = PlaywrightFormFiller().build_plan(
        profile_bundle=bundle,
        application_url="https://example.com/apply",
        resume_path="resume.pdf",
        cover_letter="Hello",
    )

    labels = {field.label for field in plan.fields}
    assert {"Name", "Email", "Phone", "LinkedIn URL", "Resume", "Cover Letter"} <= labels
    assert plan.requires_user_approval is True
    assert plan.can_submit is False
