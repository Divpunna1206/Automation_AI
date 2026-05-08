from fastapi import APIRouter, Depends, HTTPException

from app.core.config_loader import ProfileBundle, get_profile_bundle
from app.core.settings import Settings, get_settings
from app.db.repository import ApplicationRepository, get_application_repository
from app.models.application import (
    ApplicationListResponse,
    ApplicationSaveRequest,
    ApplicationSaveResponse,
    ApplicationStatusUpdateRequest,
)
from app.models.cover_letter import CoverLetterRequest, CoverLetterResponse
from app.models.dashboard import DashboardStatsResponse
from app.models.form import FormFillPlanResponse, FormFillRequest, FormFillRunResponse
from app.models.job import (
    JobAnalyzeRequest,
    JobAnalyzeResponse,
    JobScoreRequest,
    JobScoreResponse,
    JobSearchRequest,
    JobSearchResponse,
)
from app.models.resume import ResumeGenerateRequest, ResumeGenerateResponse
from app.automation.form_filler import PlaywrightFormFiller
from app.services.cover_letter_generator import CoverLetterGenerator
from app.services.fit_scorer import FitScorer
from app.services.job_discovery import JobDiscoveryService
from app.services.jd_parser import JDParser
from app.services.resume_tailor import ResumeTailor

router = APIRouter()


@router.post("/jobs/search", response_model=JobSearchResponse)
def search_jobs(
    payload: JobSearchRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
    settings: Settings = Depends(get_settings),
) -> JobSearchResponse:
    return JobDiscoveryService(settings, FitScorer(profile)).search(payload)


@router.post("/jobs/analyze", response_model=JobAnalyzeResponse)
def analyze_job(payload: JobAnalyzeRequest) -> JobAnalyzeResponse:
    parsed = JDParser().parse(payload)
    return JobAnalyzeResponse(job=parsed)


@router.post("/jobs/score", response_model=JobScoreResponse)
def score_job(
    payload: JobScoreRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
) -> JobScoreResponse:
    score = FitScorer(profile).score(payload.job)
    return JobScoreResponse(score=score)


@router.post("/resumes/generate", response_model=ResumeGenerateResponse)
def generate_resume(
    payload: ResumeGenerateRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
) -> ResumeGenerateResponse:
    return ResumeTailor(profile).generate(payload)


@router.post("/cover-letter/generate", response_model=CoverLetterResponse)
def generate_cover_letter(
    payload: CoverLetterRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
) -> CoverLetterResponse:
    return CoverLetterGenerator(profile).generate(payload)


@router.post("/applications/save", response_model=ApplicationSaveResponse)
def save_application(
    payload: ApplicationSaveRequest,
    repo: ApplicationRepository = Depends(get_application_repository),
) -> ApplicationSaveResponse:
    application = repo.save(payload)
    return ApplicationSaveResponse(application=application)


@router.get("/applications", response_model=ApplicationListResponse)
def list_applications(
    repo: ApplicationRepository = Depends(get_application_repository),
) -> ApplicationListResponse:
    return repo.list_applications()


@router.patch("/applications/{application_id}/status", response_model=ApplicationSaveResponse)
def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdateRequest,
    repo: ApplicationRepository = Depends(get_application_repository),
) -> ApplicationSaveResponse:
    try:
        application = repo.update_status(application_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApplicationSaveResponse(application=application)


@router.post("/forms/fill-plan", response_model=FormFillPlanResponse)
def create_form_fill_plan(
    payload: FormFillRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
) -> FormFillPlanResponse:
    return PlaywrightFormFiller().build_plan(
        profile_bundle=profile,
        application_url=payload.application_url,
        resume_path=payload.resume_path,
        cover_letter=payload.cover_letter,
    )


@router.post("/forms/fill", response_model=FormFillRunResponse)
async def fill_form_until_review(
    payload: FormFillRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
) -> FormFillRunResponse:
    plan = PlaywrightFormFiller().build_plan(
        profile_bundle=profile,
        application_url=payload.application_url,
        resume_path=payload.resume_path,
        cover_letter=payload.cover_letter,
    )
    if payload.dry_run:
        return FormFillRunResponse(
            status="dry_run",
            message="Dry run requested. Fill plan generated but browser automation was not launched.",
        )
    return await PlaywrightFormFiller().run_until_review(plan)


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    repo: ApplicationRepository = Depends(get_application_repository),
) -> DashboardStatsResponse:
    return repo.dashboard_stats()
