from dataclasses import dataclass

from playwright.async_api import async_playwright

from app.core.config_loader import ProfileBundle
from app.models.form import FillField, FormFillPlanResponse, FormFillRunResponse


@dataclass(frozen=True)
class FillPlan:
    url: str
    fields: dict[str, str]
    requires_user_approval: bool = True


class ApplicationFormFiller:
    """Prepares browser automation without submitting applications in Phase 1."""

    async def prepare_fill_plan(self, url: str, fields: dict[str, str]) -> FillPlan:
        return FillPlan(url=url, fields=fields, requires_user_approval=True)

    async def submit(self) -> None:
        raise RuntimeError("Automatic submission is intentionally disabled. User approval is always required.")


class PlaywrightFormFiller:
    def build_plan(
        self,
        profile_bundle: ProfileBundle,
        application_url: str,
        resume_path: str | None,
        cover_letter: str | None,
    ) -> FormFillPlanResponse:
        profile = profile_bundle.profile
        fields = [
            FillField(label="Name", value=profile.name, selector_candidates=["input[name*=name i]", "#name"]),
            FillField(label="Email", value=profile.email, selector_candidates=["input[type=email]", "input[name*=email i]"]),
            FillField(label="Phone", value=profile.phone or "", selector_candidates=["input[type=tel]", "input[name*=phone i]"]),
            FillField(label="LinkedIn URL", value=profile.linkedin or "", selector_candidates=["input[name*=linkedin i]"]),
            FillField(label="Resume", value=resume_path or "", selector_candidates=["input[type=file]"], kind="file"),
            FillField(label="Cover Letter", value=cover_letter or "", selector_candidates=["textarea[name*=cover i]", "textarea"]),
        ]
        return FormFillPlanResponse(
            application_url=application_url,
            fields=[field for field in fields if field.value],
            requires_user_approval=True,
            can_submit=False,
            message="Fill plan created. Review before launching automation; final submit remains disabled.",
        )

    async def run_until_review(self, plan: FormFillPlanResponse) -> FormFillRunResponse:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto(plan.application_url, wait_until="domcontentloaded")
            for field in plan.fields:
                await self._try_fill(page, field)
            await page.pause()
            await browser.close()
        return FormFillRunResponse(
            status="review_required",
            message="Form fields were attempted and browser paused for user review. No submit action was taken.",
        )

    async def _try_fill(self, page, field: FillField) -> None:
        for selector in field.selector_candidates:
            try:
                locator = page.locator(selector).first
                if await locator.count() == 0:
                    continue
                if field.kind == "file":
                    await locator.set_input_files(field.value)
                else:
                    await locator.fill(field.value)
                return
            except Exception:
                continue
