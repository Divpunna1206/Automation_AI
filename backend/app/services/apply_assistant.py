from pathlib import Path

from app.core.config_loader import ProfileBundle
from app.core.settings import ROOT_DIR
from app.db.apply_session_repository import ApplySessionRepository
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.db.resume_version_repository import ResumeVersionRepository
from app.models.apply_session import (
    ApplySessionCreateRequest,
    ApplySessionCreateResponse,
    ApplySessionRecord,
    ApplySessionStatus,
    FieldResult,
)
from app.models.form import FillField


class ApplyAssistantService:
    def __init__(
        self,
        profile_bundle: ProfileBundle,
        session_repository: ApplySessionRepository,
        queue_repository: DiscoveryQueueRepository,
        application_repository: ApplicationRepository,
        resume_repository: ResumeVersionRepository,
    ):
        self.profile_bundle = profile_bundle
        self.session_repository = session_repository
        self.queue_repository = queue_repository
        self.application_repository = application_repository
        self.resume_repository = resume_repository

    def create_apply_session(self, payload: ApplySessionCreateRequest) -> ApplySessionCreateResponse:
        resolved = self._resolve_context(payload)
        if not resolved.get("job_url"):
            raise ValueError("A job URL is required to start an apply session.")
        resume_version_id, resume_file_path, resume_warning = self._resolve_resume(payload, resolved)
        cover_letter = payload.cover_letter_text or resolved.get("cover_letter_text")
        plan = self.build_fill_plan(resolved["job_url"], resume_file_path, cover_letter)
        field_results = [
            FieldResult(label=field.label, status="planned", message="Ready to attempt fill.", confidence="medium")
            for field in plan
        ]
        errors = [resume_warning] if resume_warning else []
        session = self.session_repository.create(
            job_queue_id=payload.job_queue_id,
            application_id=payload.application_id,
            job_url=resolved["job_url"],
            company=resolved["company"],
            title=resolved["title"],
            resume_version_id=resume_version_id,
            resume_file_path=resume_file_path,
            cover_letter_text=cover_letter,
            fill_summary="Fill plan created. Review manually. Submit yourself if everything is correct.",
            field_results=field_results,
            errors=errors,
        )
        return ApplySessionCreateResponse(
            session=session,
            fill_plan=plan,
            message="Apply session planned. Final submit is blocked; you must review and submit manually.",
        )

    def build_fill_plan(self, application_url: str, resume_path: str | None, cover_letter: str | None) -> list[FillField]:
        profile = self.profile_bundle.profile
        answers = self.profile_bundle.answers
        fields = [
            FillField(label="Name", value=profile.name, selector_candidates=self._selectors("name")),
            FillField(label="Email", value=profile.email, selector_candidates=["input[type=email]", *self._selectors("email")]),
            FillField(label="Phone", value=profile.phone or "", selector_candidates=["input[type=tel]", *self._selectors("phone")]),
            FillField(label="Location", value=profile.location or "", selector_candidates=self._selectors("location")),
            FillField(label="LinkedIn URL", value=profile.linkedin or "", selector_candidates=self._selectors("linkedin")),
            FillField(label="GitHub URL", value=profile.github or "", selector_candidates=self._selectors("github")),
            FillField(label="Portfolio URL", value="", selector_candidates=self._selectors("portfolio")),
            FillField(label="Expected Salary", value=answers.salary_expectation or "", selector_candidates=self._selectors("salary")),
            FillField(label="Notice Period", value=answers.notice_period or "", selector_candidates=self._selectors("notice")),
            FillField(label="Cover Letter", value=cover_letter or "", selector_candidates=["textarea[name*=cover i]", "textarea[placeholder*=cover i]", "textarea"], kind="textarea"),
            FillField(label="Resume", value=resume_path or "", selector_candidates=["input[type=file]", "input[name*=resume i]", "input[id*=resume i]"], kind="file"),
        ]
        return [field for field in fields if field.value]

    async def run_until_review(self, session_id: int, runner=None) -> ApplySessionRecord:
        session = self.session_repository.update(session_id, status=ApplySessionStatus.RUNNING)
        plan = self.build_fill_plan(session.job_url, session.resume_file_path, session.cover_letter_text)
        active_runner = runner or PlaywrightApplyRunner()
        try:
            results, screenshots, errors = await active_runner.run(session.id, session.job_url, plan)
            summary = "Review manually. Submit yourself if everything is correct. Submit buttons are blocked/manual."
            return self.session_repository.update(
                session_id,
                status=ApplySessionStatus.REVIEW_REQUIRED,
                fill_summary=summary,
                field_results=results,
                screenshot_paths=screenshots,
                errors=errors,
            )
        except Exception as exc:
            return self.mark_failed(session_id, f"Unsupported or failed page. Review manually. Error: {exc}")

    def mark_completed_manually(self, session_id: int, message: str | None = None) -> ApplySessionRecord:
        return self.session_repository.update(
            session_id,
            status=ApplySessionStatus.COMPLETED_MANUALLY,
            fill_summary=message or "User marked this application completed manually.",
        )

    def mark_failed(self, session_id: int, message: str) -> ApplySessionRecord:
        current = self.session_repository.get(session_id)
        return self.session_repository.update(
            session_id,
            status=ApplySessionStatus.FAILED,
            fill_summary=message,
            errors=[*current.errors, message],
        )

    def list_apply_sessions(self):
        return self.session_repository.list_sessions()

    def get_apply_session(self, session_id: int) -> ApplySessionRecord:
        return self.session_repository.get(session_id)

    def _resolve_context(self, payload: ApplySessionCreateRequest) -> dict[str, str | None]:
        if payload.job_queue_id is not None:
            job = self.queue_repository.get(payload.job_queue_id)
            return {
                "job_url": job.job_url,
                "company": job.company,
                "title": job.title,
                "cover_letter_text": payload.cover_letter_text,
            }
        if payload.application_id is not None:
            application = self.application_repository.get(payload.application_id)
            return {
                "job_url": application.job_url,
                "company": application.company,
                "title": application.title,
                "cover_letter_text": application.cover_letter,
            }
        return {
            "job_url": payload.job_url,
            "company": payload.company or "Unknown",
            "title": payload.title or "Application",
            "cover_letter_text": payload.cover_letter_text,
        }

    def _resolve_resume(self, payload: ApplySessionCreateRequest, context: dict[str, str | None]) -> tuple[int | None, str | None, str | None]:
        if payload.resume_file_path:
            return payload.resume_version_id, payload.resume_file_path, None
        if payload.resume_version_id is not None:
            version = self.resume_repository.get(payload.resume_version_id)
            return version.id, version.file_path, None if version.file_path else "Selected resume version has no PDF path."
        versions = self.resume_repository.list_versions(limit=100).versions
        linked = [
            version for version in versions
            if (payload.job_queue_id is not None and version.job_queue_id == payload.job_queue_id)
            or (payload.application_id is not None and version.application_id == payload.application_id)
        ]
        selected = next((version for version in linked if version.status.value == "selected"), None)
        fallback = selected or (linked[0] if linked else (versions[0] if versions else None))
        if fallback:
            return fallback.id, fallback.file_path, None if fallback.file_path else "Latest resume version has no PDF path."
        return None, None, "No resume version found; upload skipped and manual review required."

    def _selectors(self, token: str) -> list[str]:
        return [
            f"input[name*={token} i]",
            f"input[id*={token} i]",
            f"input[placeholder*={token} i]",
            f"textarea[name*={token} i]",
            f"textarea[id*={token} i]",
            f"textarea[placeholder*={token} i]",
        ]


class PlaywrightApplyRunner:
    async def run(self, session_id: int, job_url: str, plan: list[FillField]) -> tuple[list[FieldResult], list[str], list[str]]:
        from playwright.async_api import async_playwright

        screenshot_dir = ROOT_DIR / "backend" / "artifacts" / "apply_sessions"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"apply-session-{session_id}-review.png"
        results: list[FieldResult] = []
        errors: list[str] = []

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto(job_url, wait_until="domcontentloaded")
            for field in plan:
                results.append(await self._try_fill(page, field))
            submit_count = await page.locator("button[type=submit], input[type=submit], button:has-text('Submit'), button:has-text('Apply')").count()
            if submit_count:
                results.append(
                    FieldResult(
                        label="Final Submit",
                        status="blocked_manual",
                        message="Submit button detected and intentionally not clicked. Review manually.",
                        confidence="high",
                    )
                )
            await page.screenshot(path=str(screenshot_path), full_page=True)
            await page.pause()
            await browser.close()
        return results, [str(screenshot_path)], errors

    async def _try_fill(self, page, field: FillField) -> FieldResult:
        candidates = field.selector_candidates[:5]
        for selector in candidates:
            try:
                locator = page.locator(selector).first
                if await locator.count() == 0:
                    continue
                if field.kind == "file":
                    if not Path(field.value).exists():
                        return FieldResult(label=field.label, status="skipped", message="Resume file not found; manual upload required.", selector=selector, confidence="high")
                    await locator.set_input_files(field.value)
                else:
                    await locator.fill(field.value)
                return FieldResult(label=field.label, status="filled", message="Field filled for manual review.", selector=selector, confidence="medium")
            except Exception:
                continue
        return FieldResult(label=field.label, status="skipped", message="No confident selector matched; manual review required.", confidence="low")
