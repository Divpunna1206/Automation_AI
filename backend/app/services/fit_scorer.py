from app.core.config_loader import ProfileBundle
from app.models.job import FitScore, ParsedJob


class FitScorer:
    def __init__(self, profile_bundle: ProfileBundle):
        self.profile_bundle = profile_bundle

    def score(self, job: ParsedJob) -> FitScore:
        profile = self.profile_bundle.profile
        preferences = self.profile_bundle.preferences
        profile_skills = {skill.lower() for skill in profile.skills}
        required = {skill.lower() for skill in job.required_skills}

        matched = sorted(required & profile_skills)
        missing = sorted(required - profile_skills)

        skill_signal = 60 if not required else round((len(matched) / len(required)) * 60)
        title_signal = self._title_signal(job.title, preferences.target_titles)
        location_signal = 10 if not preferences.target_locations or self._matches_any(job.location or "", preferences.target_locations) else 2
        keyword_signal = min(10, sum(2 for keyword in preferences.preferred_keywords if keyword.lower() in job.description.lower()))
        seniority_signal = self._seniority_signal(job.seniority)
        reputation_signal = self._reputation_signal(job.company_reputation)

        concerns = list(job.risk_flags)
        for keyword in preferences.excluded_keywords:
            if keyword.lower() in job.description.lower():
                concerns.append(f"Contains excluded keyword: {keyword}")

        score = max(
            0,
            min(
                100,
                skill_signal
                + title_signal
                + location_signal
                + keyword_signal
                + seniority_signal
                + reputation_signal
                - len(concerns) * 10,
            ),
        )
        recommendation = "approve" if score >= preferences.min_fit_score and not concerns else "review"
        if score < 50 or any("excluded keyword" in concern.lower() for concern in concerns):
            recommendation = "skip"

        return FitScore(
            score=score,
            recommendation=recommendation,
            matched_skills=matched,
            missing_skills=missing,
            concerns=concerns,
            rationale=(
                f"Matched {len(matched)} of {len(required)} parsed required skills, "
                "then adjusted for title, seniority, location, keywords, and company signal."
            ),
            signals={
                "skills": skill_signal,
                "title": title_signal,
                "location": location_signal,
                "keywords": keyword_signal,
                "seniority": seniority_signal,
                "company_reputation": reputation_signal,
            },
        )

    def _matches_any(self, value: str, candidates: list[str]) -> bool:
        lower = value.lower()
        return any(candidate.lower() in lower for candidate in candidates)

    def _title_signal(self, title: str, target_titles: list[str]) -> int:
        lower = title.lower()
        if self._matches_any(title, target_titles):
            return 15
        if "ai" in lower and any(word in lower for word in ("engineer", "developer", "product")):
            return 12
        if any(word in lower for word in ("software", "full-stack", "backend", "developer")):
            return 8
        return 3

    def _seniority_signal(self, seniority: str | None) -> int:
        if seniority in {"mid-level", "senior", "lead", "staff"}:
            return 8
        if seniority in {"junior", "entry", "internship"}:
            return 2
        return 5

    def _reputation_signal(self, company_reputation: int | None) -> int:
        if company_reputation is None:
            return 3
        return round((company_reputation / 100) * 7)
