from app.core.config_loader import ProfileBundle
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.models.ats import ATSAnalyzeRequest, ATSAnalyzeResponse, GapActionItem
from app.models.job import JobAnalyzeRequest, ParsedJob
from app.services.jd_parser import JDParser


class ATSAnalyzer:
    def __init__(
        self,
        profile_bundle: ProfileBundle,
        queue_repository: DiscoveryQueueRepository | None = None,
        application_repository: ApplicationRepository | None = None,
    ):
        self.profile_bundle = profile_bundle
        self.queue_repository = queue_repository
        self.application_repository = application_repository
        self.parser = JDParser()

    def analyze(self, request: ATSAnalyzeRequest) -> ATSAnalyzeResponse:
        job = self._resolve_job(request)
        profile = self.profile_bundle.profile
        profile_keywords = self._profile_keywords()
        required = [item.lower() for item in job.required_skills]
        preferred = [item.lower() for item in job.preferred_skills]
        domain = [item.lower() for item in job.domain_keywords]
        job_keywords = sorted(set(required + preferred + domain + [tool.lower() for tool in job.tools]))

        matched_keywords = sorted(keyword for keyword in job_keywords if keyword in profile_keywords)
        missing_keywords = sorted(keyword for keyword in job_keywords if keyword not in profile_keywords)
        matched_projects = self._matched_projects(job_keywords)
        resume_gaps = [f"Missing requested keyword or skill: {keyword}" for keyword in missing_keywords]
        action_plan = self.gap_action_plan(missing_keywords, profile_keywords)

        required_match = self._ratio([skill for skill in required if skill not in preferred], profile_keywords)
        preferred_match = self._ratio(preferred, profile_keywords)
        keyword_match = self._ratio(job_keywords, profile_keywords)
        project_signal = min(10, len(matched_projects) * 3)
        ats_score = round((required_match * 55) + (preferred_match * 15) + (keyword_match * 20) + project_signal)
        ats_score = max(0, min(100, ats_score))

        warnings = []
        if ats_score < 60:
            warnings.append("ATS score is below 60; review gaps before applying.")
        if missing_keywords:
            warnings.append("Missing JD keywords were not inserted into the resume.")

        return ATSAnalyzeResponse(
            ats_score=ats_score,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            required_skills_detected=job.required_skills,
            preferred_skills_detected=job.preferred_skills,
            matched_projects=matched_projects,
            resume_gaps=resume_gaps,
            recommended_resume_angle=self._recommended_angle(job, matched_keywords),
            improvement_suggestions=self._improvement_suggestions(ats_score, missing_keywords, matched_keywords),
            missing_keyword_action_plan=action_plan,
            profile_update_suggestions=self._profile_update_suggestions(action_plan),
            safe_phrasing_suggestions=self._safe_phrasing_suggestions(action_plan),
            warnings=warnings,
            truthfulness_notes=[
                "Only profile.yaml skills, experience, education, certifications, and highlights are eligible for resume content.",
                "Missing JD skills remain gaps and are never inserted as claimed experience.",
                "No company names, years, metrics, degrees, certifications, or projects are invented.",
            ],
            job=job,
        )

    def _resolve_job(self, request: ATSAnalyzeRequest) -> ParsedJob:
        if request.job:
            return request.job
        if request.job_queue_id is not None and self.queue_repository is not None:
            queue_job = self.queue_repository.get(request.job_queue_id)
            return self.parser.parse(
                JobAnalyzeRequest(
                    title=queue_job.title,
                    company=queue_job.company,
                    description=queue_job.description,
                    url=queue_job.job_url,
                    location=queue_job.location,
                    source=queue_job.source,
                )
            )
        if request.application_id is not None and self.application_repository is not None:
            application = self.application_repository.get(request.application_id)
            description = application.resume_markdown or application.notes or f"{application.title} at {application.company}"
            return self.parser.parse(
                JobAnalyzeRequest(
                    title=application.title,
                    company=application.company,
                    description=description,
                    url=application.job_url,
                    source=application.source,
                )
            )
        if request.title and request.company and request.description:
            return self.parser.parse(
                JobAnalyzeRequest(
                    title=request.title,
                    company=request.company,
                    description=request.description,
                    source="manual",
                )
            )
        raise ValueError("Provide a parsed job, job_queue_id, or title/company/description.")

    def _profile_keywords(self) -> set[str]:
        profile = self.profile_bundle.profile
        keywords = {skill.lower() for skill in profile.skills}
        for item in profile.experience:
            keywords.update(skill.lower() for skill in item.skills)
            for highlight in item.highlights:
                lower = highlight.lower()
                for token in keywords.copy():
                    if token in lower:
                        keywords.add(token)
        keywords.update(cert.lower() for cert in profile.certifications)
        return {keyword.strip() for keyword in keywords if keyword and keyword.strip()}

    def _matched_projects(self, keywords: list[str]) -> list[str]:
        matches = []
        for item in self.profile_bundle.profile.experience:
            haystack = " ".join(item.highlights + item.skills).lower()
            if any(keyword in haystack for keyword in keywords):
                matches.append(f"{item.title} at {item.company}")
        return matches[:5]

    def _ratio(self, keywords: list[str], profile_keywords: set[str]) -> float:
        unique = sorted(set(keywords))
        if not unique:
            return 1.0
        return len([keyword for keyword in unique if keyword in profile_keywords]) / len(unique)

    def _recommended_angle(self, job: ParsedJob, matched_keywords: list[str]) -> str:
        if matched_keywords:
            return f"Lead with verified {', '.join(matched_keywords[:5])} experience for the {job.title} role."
        return f"Use a truthful general software engineering angle for the {job.title} role and call out gaps before applying."

    def gap_action_plan(self, missing_keywords: list[str], profile_keywords: set[str] | None = None) -> list[GapActionItem]:
        profile_terms = profile_keywords if profile_keywords is not None else self._profile_keywords()
        items = []
        for index, skill in enumerate(missing_keywords):
            gap_type = "adjacent" if self._has_adjacent_skill(skill, profile_terms) else "missing"
            priority = "high" if index < 3 else "medium"
            items.append(
                GapActionItem(
                    skill=skill,
                    gap_type=gap_type,
                    priority=priority,
                    safe_resume_action=(
                        f"Do not add {skill} as a skill unless it is true. "
                        "If you have related exposure, mention only the verified adjacent work."
                    ),
                    learning_action=f"Complete a small practical exercise with {skill} and add it later only after real use.",
                    interview_preparation_note=f"Prepare an honest answer about current {skill} exposure and how you would ramp up.",
                )
            )
        return items

    def _has_adjacent_skill(self, skill: str, profile_terms: set[str]) -> bool:
        adjacency = {
            "docker": {"deployment", "kubernetes", "backend", "fastapi"},
            "kubernetes": {"docker", "deployment", "backend"},
            "redis": {"cache", "celery", "backend"},
            "graphql": {"api", "backend", "react"},
            "aws": {"cloud", "deployment", "backend"},
            "langchain": {"llm", "openai", "rag"},
        }
        return bool(adjacency.get(skill, set()) & profile_terms)

    def _improvement_suggestions(self, score: int, missing_keywords: list[str], matched_keywords: list[str]) -> list[str]:
        suggestions = []
        if matched_keywords:
            suggestions.append(f"Move verified {', '.join(matched_keywords[:4])} keywords into the top skills and summary.")
        if missing_keywords:
            suggestions.append("Keep missing JD keywords in the gap report; do not add them to the resume as claimed skills.")
        if score < 60:
            suggestions.append("Consider skipping or doing focused learning before applying because ATS score is below 60.")
        return suggestions

    def _profile_update_suggestions(self, items: list[GapActionItem]) -> list[str]:
        return [
            f"After real practice, update profile.yaml with {item.skill} only if you can explain concrete usage."
            for item in items[:5]
        ]

    def _safe_phrasing_suggestions(self, items: list[GapActionItem]) -> list[str]:
        return [
            f"For {item.skill}: use phrasing like 'exposure to related tooling' only when supported by verified experience."
            for item in items[:5]
        ]
