import re

from app.models.job import JobAnalyzeRequest, ParsedJob


KNOWN_SKILLS = {
    "python",
    "fastapi",
    "django",
    "flask",
    "typescript",
    "javascript",
    "react",
    "next.js",
    "node.js",
    "sql",
    "postgresql",
    "sqlite",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "playwright",
    "openai",
    "llm",
    "rag",
    "langchain",
    "celery",
    "redis",
    "graphql",
}


class JDParser:
    """Rule-based Phase 1 parser. An LLM provider can enrich this later."""

    def parse(self, payload: JobAnalyzeRequest) -> ParsedJob:
        text = payload.description.strip()
        lower = text.lower()
        required_skills = sorted(skill for skill in KNOWN_SKILLS if skill in lower)
        preferred_skills = self._extract_preferred_skills(lower, required_skills)

        return ParsedJob(
            title=payload.title,
            company=payload.company,
            description=text,
            url=str(payload.url) if payload.url else None,
            location=payload.location,
            source=payload.source,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            responsibilities=self._extract_bullets(text),
            seniority=self._detect_seniority(lower),
            employment_type=self._detect_employment_type(lower),
            risk_flags=self._detect_risks(lower),
        )

    def _extract_bullets(self, text: str) -> list[str]:
        candidates = []
        for line in text.splitlines():
            clean = re.sub(r"^[\s\-*•]+", "", line).strip()
            if len(clean) > 25 and any(word in clean.lower() for word in ("build", "design", "develop", "lead", "own", "collaborate")):
                candidates.append(clean)
        if candidates:
            return candidates[:8]
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [sentence.strip() for sentence in sentences if 40 <= len(sentence.strip()) <= 220][:5]

    def _extract_preferred_skills(self, lower: str, required: list[str]) -> list[str]:
        preferred_context = "preferred" in lower or "nice to have" in lower or "bonus" in lower
        if not preferred_context:
            return []
        return required[-5:]

    def _detect_seniority(self, lower: str) -> str | None:
        for seniority in ("principal", "staff", "senior", "lead", "mid-level", "junior", "entry"):
            if seniority in lower:
                return seniority
        return None

    def _detect_employment_type(self, lower: str) -> str | None:
        if "contract" in lower:
            return "contract"
        if "part-time" in lower:
            return "part-time"
        if "intern" in lower:
            return "internship"
        if "full-time" in lower or "full time" in lower:
            return "full-time"
        return None

    def _detect_risks(self, lower: str) -> list[str]:
        flags = []
        if "unpaid" in lower:
            flags.append("Mentions unpaid work")
        if "commission only" in lower:
            flags.append("Commission-only compensation")
        if "must have active clearance" in lower:
            flags.append("Requires active clearance")
        return flags
