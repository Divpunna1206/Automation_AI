from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from app.models.job_queue import JobParseUrlResponse


BLOCKED_DOMAINS = ("linkedin.", "naukri.", "wellfound.")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self._hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str):
        clean = " ".join(data.split())
        if not clean:
            return
        if self._in_title:
            self.title = f"{self.title} {clean}".strip()
        elif self._hidden_depth == 0:
            self.parts.append(clean)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


class JobURLParser:
    def parse(self, job_url: str) -> JobParseUrlResponse:
        parsed = urlsplit(job_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Invalid job_url. Use a full http(s) URL.")
        source = self._source_from_domain(parsed.netloc)
        if any(domain in parsed.netloc.lower() for domain in BLOCKED_DOMAINS):
            raise ValueError(
                f"{source} pages are guarded and are not fetched by this local parser. Paste the job description manually."
            )

        try:
            response = httpx.get(
                job_url,
                follow_redirects=True,
                timeout=10,
                headers={"User-Agent": "AgenticJobHuntPipeline/0.2 (+local explicit URL parser)"},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ValueError("Timed out fetching the job page. Paste the JD manually or try again later.") from exc
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"Job page returned HTTP {exc.response.status_code}. Paste the JD manually.") from exc
        except httpx.HTTPError as exc:
            raise ValueError("Could not fetch the job page. Paste the JD manually.") from exc

        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower() and response.text.lstrip().startswith("<") is False:
            raise ValueError("Fetched page did not look like HTML. Paste the JD manually.")

        extractor = TextExtractor()
        extractor.feed(response.text)
        text = " ".join(extractor.text.split())
        if len(text) < 120:
            raise ValueError("Fetched page did not contain enough readable job text. Paste the JD manually.")

        title = self._title_from_page(extractor.title, parsed.netloc)
        company = self._company_from_title(extractor.title, parsed.netloc)
        location = self._detect_location(text)

        return JobParseUrlResponse(
            title=title,
            company=company,
            job_url=str(response.url),
            source=source,
            location=location,
            description=text[:8000],
            message="Parsed page text from an explicitly provided URL. Review before saving to queue.",
        )

    def _source_from_domain(self, domain: str) -> str:
        host = domain.lower().removeprefix("www.")
        return host.split(".")[0] or "manual"

    def _title_from_page(self, title: str, domain: str) -> str:
        if title:
            return title.split("|")[0].split(" - ")[0].strip()[:140] or "Parsed job"
        return f"Job from {domain.lower()}"

    def _company_from_title(self, title: str, domain: str) -> str:
        if " - " in title:
            candidate = title.split(" - ")[-1].strip()
            if candidate:
                return candidate[:120]
        if "|" in title:
            candidate = title.split("|")[-1].strip()
            if candidate:
                return candidate[:120]
        return self._source_from_domain(domain).title()

    def _detect_location(self, text: str) -> str | None:
        lower = text.lower()
        if "remote" in lower:
            return "Remote"
        for marker in ("location:", "based in"):
            index = lower.find(marker)
            if index >= 0:
                return text[index + len(marker): index + len(marker) + 80].split(".")[0].strip()
        return None
