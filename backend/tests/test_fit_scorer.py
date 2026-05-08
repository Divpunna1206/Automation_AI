from app.core.config_loader import Answers, ExperienceItem, Preferences, Profile, ProfileBundle
from app.models.job import ParsedJob
from app.services.fit_scorer import FitScorer


def profile_bundle() -> ProfileBundle:
    return ProfileBundle(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            summary="Applied AI developer",
            skills=["Python", "FastAPI", "React", "OpenAI", "Playwright", "SQL"],
            experience=[
                ExperienceItem(
                    company="AI Co",
                    title="Applied AI Developer",
                    start="2022",
                    end="Present",
                    highlights=["Built OpenAI and FastAPI workflows."],
                    skills=["Python", "FastAPI"],
                )
            ],
        ),
        preferences=Preferences(
            target_titles=["AI Product Engineer", "Applied AI Developer"],
            target_locations=["Remote"],
            preferred_keywords=["human-in-the-loop", "OpenAI"],
            excluded_keywords=["unpaid"],
            min_fit_score=70,
        ),
        answers=Answers(),
    )


def test_fit_scorer_recommends_strong_ai_match() -> None:
    job = ParsedJob(
        title="AI Product Engineer",
        company="Acme AI",
        description="Build human-in-the-loop OpenAI systems with FastAPI, React, SQL, and Playwright.",
        location="Remote",
        source="test",
        required_skills=["python", "fastapi", "react", "openai", "sql"],
        seniority="senior",
        company_reputation=80,
    )

    score = FitScorer(profile_bundle()).score(job)

    assert score.score >= 80
    assert score.recommendation == "approve"
    assert score.signals["skills"] == 60
    assert "python" in score.matched_skills


def test_fit_scorer_skips_excluded_keyword() -> None:
    job = ParsedJob(
        title="Junior Developer",
        company="Unknown",
        description="Unpaid internship requiring Rust.",
        location="Onsite",
        source="test",
        required_skills=["rust"],
        seniority="junior",
    )

    score = FitScorer(profile_bundle()).score(job)

    assert score.recommendation == "skip"
    assert any("excluded keyword" in concern.lower() for concern in score.concerns)
