from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sqlite3
import uuid

from fastapi import Depends

from app.core.config_loader import load_profile_bundle
from app.core.settings import Settings, get_settings
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.outreach_repository import OutreachRepository
from app.db.repository import ApplicationRepository
from app.db.resume_version_repository import ResumeVersionRepository
from app.db.sqlite import get_connection, init_db
from app.models.application import ApplicationSaveRequest, ApplicationStatus
from app.models.job_queue import DiscoveredJobSaveRequest
from app.models.outreach import OutreachChannel, OutreachContactCreate, OutreachMessageType, OutreachRecordCreate, OutreachStatus
from app.models.resume import ResumeVersionStatus
from app.models.system import DemoSeedResponse, SystemHealthCheckResponse


class SystemService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def health_check(self) -> SystemHealthCheckResponse:
        warnings: list[str] = []
        database_reachable = self._database_reachable(warnings)
        config_valid = self._config_valid(warnings)
        artifacts_writable = self._artifacts_writable(warnings)
        playwright_status = self._playwright_status(warnings)
        llm_status = self._llm_status(warnings)
        return SystemHealthCheckResponse(
            backend_status="ok",
            database_reachable=database_reachable,
            config_valid=config_valid,
            artifacts_writable=artifacts_writable,
            playwright_status=playwright_status,
            llm_status=llm_status,
            frontend_api_base_url_suggestion="NEXT_PUBLIC_API_BASE_URL=http://localhost:8000",
            warnings=warnings,
        )

    def seed_demo_data(self) -> DemoSeedResponse:
        init_db(self.settings.database_url)
        suffix = uuid.uuid4().hex[:8]
        queue_repo = DiscoveryQueueRepository(self.settings.database_url)
        application_repo = ApplicationRepository(self.settings.database_url)
        resume_repo = ResumeVersionRepository(self.settings.database_url)
        outreach_repo = OutreachRepository(self.settings.database_url)

        jobs = [
            ("AI Product Engineer", "Demo Acme AI", "remoteok", 86, ["Python", "FastAPI", "LLM"]),
            ("Full Stack AI Engineer", "Demo Beta Labs", "manual", 74, ["React", "FastAPI", "SQLite"]),
            ("Applied AI Engineer", "Demo Gamma Works", "remoteok", 68, ["Python", "RAG", "Docker"]),
            ("Backend Automation Engineer", "Demo Delta Systems", "manual", 59, ["Playwright", "APIs"]),
        ]
        created_jobs = 0
        for index, (title, company, source, fit, skills) in enumerate(jobs, start=1):
            result = queue_repo.save_discovered_job(
                DiscoveredJobSaveRequest(
                    title=title,
                    company=company,
                    job_url=f"https://demo.local/jobs/{suffix}/{index}",
                    source=source,
                    location="Remote",
                    work_mode="remote",
                    description=f"Demo job for {title}. Requires {', '.join(skills)} and human-approved application workflow.",
                    required_skills=skills,
                    fit_score=fit,
                    recommendation="approve" if fit >= 75 else "review",
                )
            )
            if result.created:
                created_jobs += 1

        app_one = application_repo.save(
            ApplicationSaveRequest(
                company="Demo Acme AI",
                title="AI Product Engineer",
                job_url=f"https://demo.local/applications/{suffix}/1",
                source="remoteok",
                fit_score=86,
                recommendation="approve",
                status=ApplicationStatus.INTERVIEW,
                follow_up_date=date.today() + timedelta(days=3),
                notes="Demo application for analytics testing.",
            )
        )
        application_repo.save(
            ApplicationSaveRequest(
                company="Demo Beta Labs",
                title="Full Stack AI Engineer",
                job_url=f"https://demo.local/applications/{suffix}/2",
                source="manual",
                fit_score=61,
                recommendation="review",
                status=ApplicationStatus.REJECTED,
                notes="Demo rejected application for funnel analytics.",
            )
        )

        created_resume_versions = 0
        for version_id, title, company, ats, missing in [
            (f"demo-ai-product-{suffix}", "AI Product Engineer", "Demo Acme AI", 88, ["Docker", "Kubernetes"]),
            (f"demo-full-stack-{suffix}", "Full Stack AI Engineer", "Demo Beta Labs", 63, ["Docker", "AWS"]),
        ]:
            record = resume_repo.create(
                resume_version_id=version_id,
                application_id=app_one.id if "product" in version_id else None,
                title=title,
                company=company,
                ats_score=ats,
                matched_keywords=["Python", "FastAPI"],
                missing_keywords=missing,
                file_path=f"backend/artifacts/resumes/{version_id}.pdf",
                file_path_docx=f"backend/artifacts/resumes/{version_id}.docx",
            )
            if "product" in version_id:
                resume_repo.update_status(record.id, ResumeVersionStatus.SELECTED)
            created_resume_versions += 1

        contact_one = outreach_repo.create_contact(
            OutreachContactCreate(company="Demo Acme AI", name="Demo Recruiter", title="Talent Partner", source="manual")
        )
        contact_two = outreach_repo.create_contact(
            OutreachContactCreate(company="Demo Beta Labs", name="Demo Hiring Manager", title="Engineering Manager", source="manual")
        )
        outreach_repo.create_record(
            OutreachRecordCreate(
                application_id=app_one.id,
                contact_id=contact_one.id,
                channel=OutreachChannel.LINKEDIN,
                message_text="Demo manual LinkedIn note. User sends outside the app.",
                status=OutreachStatus.REPLIED,
                follow_up_date=date.today(),
            )
        )
        outreach_repo.create_record(
            OutreachRecordCreate(
                contact_id=contact_two.id,
                channel=OutreachChannel.EMAIL,
                message_type=OutreachMessageType.FOLLOW_UP_1,
                message_text="Demo follow-up draft. User sends outside the app.",
                status=OutreachStatus.NO_RESPONSE,
                follow_up_date=date.today() - timedelta(days=1),
            )
        )
        return DemoSeedResponse(
            created_jobs=created_jobs,
            created_applications=2,
            created_resume_versions=created_resume_versions,
            created_contacts=2,
            created_outreach_records=2,
            message="Demo data created locally with fake companies and no secrets.",
        )

    def _database_reachable(self, warnings: list[str]) -> bool:
        try:
            with get_connection(self.settings.database_url) as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error as exc:
            warnings.append(f"Database check failed: {exc}")
            return False

    def _config_valid(self, warnings: list[str]) -> bool:
        try:
            load_profile_bundle(self.settings.profile_path, self.settings.preferences_path, self.settings.answers_path)
            return True
        except Exception as exc:
            warnings.append(f"Config validation failed: {exc}")
            return False

    def _artifacts_writable(self, warnings: list[str]) -> bool:
        try:
            self.settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
            probe = Path(self.settings.artifacts_dir) / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError as exc:
            warnings.append(f"Artifacts directory is not writable: {exc}")
            return False

    def _playwright_status(self, warnings: list[str]) -> str:
        if importlib.util.find_spec("playwright") is None:
            warnings.append("Playwright package is missing. Apply Assistant browser flow will not run.")
            return "missing"
        return "installed"

    def _llm_status(self, warnings: list[str]) -> str:
        provider = self.settings.llm_provider.lower()
        if provider in {"openai", "openai-compatible"} and self.settings.openai_api_key:
            return "openai-compatible configured"
        if provider in {"openai", "openai-compatible"} and not self.settings.openai_api_key:
            warnings.append("OpenAI-compatible provider selected but OPENAI_API_KEY is missing; local fallback behavior is recommended.")
            return "openai key missing"
        return "local fallback active"


def get_system_service(settings: Settings = Depends(get_settings)) -> SystemService:
    return SystemService(settings)
