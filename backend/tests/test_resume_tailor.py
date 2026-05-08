from pathlib import Path

from app.core.config_loader import Answers, ExperienceItem, Preferences, Profile, ProfileBundle
from app.models.job import ParsedJob
from app.models.resume import ResumeGenerateRequest
from app.services.resume_tailor import ResumeTailor


def test_resume_tailor_generates_truthful_pdf() -> None:
    bundle = ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            summary="Full-stack AI engineer",
            skills=["Python", "FastAPI", "OpenAI"],
            experience=[
                ExperienceItem(
                    company="AI Co",
                    title="Engineer",
                    start="2021",
                    end="Present",
                    highlights=["Built FastAPI systems with OpenAI integrations."],
                    skills=["Python", "FastAPI", "OpenAI"],
                )
            ],
        ),
        preferences=Preferences(),
        answers=Answers(),
    )
    job = ParsedJob(
        title="Applied AI Developer",
        company="Test Company",
        description="Need Python, FastAPI, and OpenAI.",
        source="test",
        required_skills=["python", "fastapi", "openai"],
    )

    response = ResumeTailor(bundle).generate(ResumeGenerateRequest(job=job))

    assert "FastAPI" in response.resume_markdown
    assert response.pdf_path is not None
    assert Path(response.pdf_path).exists()
    assert "Only skills and experience present" in response.truthful_constraints[0]
