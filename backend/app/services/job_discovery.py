from abc import ABC, abstractmethod

import httpx

from app.core.settings import Settings
from app.models.job import JobListing, JobSearchRequest, JobSearchResponse, ScoredJobListing
from app.services.company_reputation import CompanyReputationService
from app.services.fit_scorer import FitScorer
from app.services.jd_parser import JDParser
from app.models.job import JobAnalyzeRequest


TARGET_ROLE_TERMS = (
    "ai product engineer",
    "applied ai",
    "ai engineer",
    "llm engineer",
    "machine learning engineer",
    "full-stack ai",
    "python ai",
)


class JobSource(ABC):
    name: str

    @abstractmethod
    def search(self, request: JobSearchRequest) -> list[JobListing]:
        """Return normalized listings from one source."""


class RemoteOKSource(JobSource):
    name = "remoteok"

    def search(self, request: JobSearchRequest) -> list[JobListing]:
        response = httpx.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "AgenticJobHuntPipeline/0.2"},
            timeout=20,
        )
        response.raise_for_status()
        rows = [row for row in response.json() if isinstance(row, dict) and row.get("position")]
        listings: list[JobListing] = []
        query_terms = request.query.lower().split()

        for row in rows:
            title = str(row.get("position") or "")
            tags = [str(tag) for tag in row.get("tags") or []]
            haystack = " ".join([title, str(row.get("description") or ""), " ".join(tags)]).lower()
            if not any(term in haystack for term in query_terms + list(TARGET_ROLE_TERMS)):
                continue
            listings.append(
                JobListing(
                    title=title,
                    company=str(row.get("company") or "Unknown"),
                    description=str(row.get("description") or title),
                    url=str(row.get("url") or row.get("apply_url") or ""),
                    location=str(row.get("location") or "Remote"),
                    source=self.name,
                    tags=tags,
                )
            )
            if len(listings) >= request.limit:
                break
        return listings


class ManualURLSource(JobSource):
    name = "manual"

    def search(self, request: JobSearchRequest) -> list[JobListing]:
        return [
            JobListing(
                title="Manual job URL",
                company="Unknown",
                description=f"Manual review required for {url}. Paste the JD into manual analysis after opening the URL.",
                url=url,
                location=request.location,
                source=self.name,
                tags=["manual"],
            )
            for url in request.manual_urls
        ][: request.limit]


class DisabledScrapingSource(JobSource):
    def __init__(self, name: str, settings: Settings):
        self.name = name
        self.settings = settings

    def search(self, request: JobSearchRequest) -> list[JobListing]:
        if not self.settings.enable_web_scraping:
            raise RuntimeError(
                f"{self.name} scraping is disabled. Enable only after confirming account access, robots.txt, and site terms."
            )
        raise RuntimeError(f"{self.name} adapter requires authenticated scraping selectors or an approved API key.")


class JobDiscoveryService:
    def __init__(self, settings: Settings, scorer: FitScorer):
        self.settings = settings
        self.scorer = scorer
        self.parser = JDParser()
        self.reputation = CompanyReputationService()

    def search(self, request: JobSearchRequest) -> JobSearchResponse:
        sources = self._build_sources()
        results: list[ScoredJobListing] = []
        errors: dict[str, str] = {}

        for source_name in request.sources:
            source = sources.get(source_name.lower())
            if source is None:
                errors[source_name] = "Unknown source."
                continue
            try:
                for listing in source.search(request):
                    listing.company_reputation = self.reputation.score(listing.company)
                    parsed = self.parser.parse(
                        JobAnalyzeRequest(
                            title=listing.title,
                            company=listing.company,
                            description=listing.description,
                            url=listing.url or None,
                            location=listing.location,
                            source=listing.source,
                        )
                    )
                    parsed.company_reputation = listing.company_reputation
                    results.append(ScoredJobListing(listing=listing, parsed_job=parsed, score=self.scorer.score(parsed)))
            except Exception as exc:
                errors[source_name] = str(exc)

        results.sort(key=lambda item: item.score.score, reverse=True)
        return JobSearchResponse(results=results[: request.limit], source_errors=errors)

    def _build_sources(self) -> dict[str, JobSource]:
        return {
            "remoteok": RemoteOKSource(),
            "manual": ManualURLSource(),
            "linkedin": DisabledScrapingSource("LinkedIn", self.settings),
            "naukri": DisabledScrapingSource("Naukri", self.settings),
            "wellfound": DisabledScrapingSource("Wellfound", self.settings),
        }
