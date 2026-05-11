from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.core.config_loader import ProfileBundle, get_profile_bundle
from app.core.settings import Settings, get_settings
from app.db.apply_session_repository import ApplySessionRepository, get_apply_session_repository
from app.db.apply_question_repository import ApplyQuestionRepository, get_apply_question_repository
from app.db.discovery_queue_repository import DiscoveryQueueRepository, get_discovery_queue_repository
from app.db.outreach_repository import OutreachRepository, get_outreach_repository
from app.db.repository import ApplicationRepository, get_application_repository
from app.db.resume_version_repository import ResumeVersionRepository, get_resume_version_repository
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
from app.models.analytics import (
    AnalyticsOverviewResponse,
    OutreachPerformanceResponse,
    RecommendationsResponse,
    ResumePerformanceResponse,
    SkillGapsResponse,
    WeeklyInsightsResponse,
)
from app.models.apply_session import (
    ApplySessionCreateRequest,
    ApplySessionCreateResponse,
    ApplySessionListResponse,
    ApplySessionQuestionListResponse,
    ApplySessionQuestionRecord,
    ApplySessionReviewPack,
    ApplySessionRecord,
    ApplySessionStatusUpdateRequest,
    ApplyQuestionUpdateRequest,
)
from app.models.ats import ATSAnalyzeRequest, ATSAnalyzeResponse, GapActionPlanRequest, GapActionPlanResponse
from app.models.job_queue import (
    DailyTargetStatsResponse,
    DiscoveredJobListResponse,
    DiscoveredJobRecord,
    DiscoveredJobSaveRequest,
    JobDiscoverRequest,
    JobDiscoverResponse,
    JobParseUrlRequest,
    JobParseUrlResponse,
    JobQueueFilters,
    QueueStatus,
    QueueStatusUpdateRequest,
)
from app.models.outreach import (
    OutreachChannel,
    OutreachContactCreate,
    OutreachContactListResponse,
    OutreachContactRecord,
    OutreachContactUpdate,
    OutreachDashboardResponse,
    OutreachFollowUpMessageRequest,
    OutreachHistoryResponse,
    OutreachMessageGenerateRequest,
    OutreachMessageGenerateResponse,
    OutreachRecordCreate,
    OutreachRecordListResponse,
    OutreachRecordRecord,
    OutreachRecordStatusUpdate,
    OutreachSearchSuggestionRequest,
    OutreachSearchSuggestionResponse,
    OutreachStatus,
)
from app.models.resume import (
    ResumeGenerateRequest,
    ResumeGenerateResponse,
    ResumeGenerateTailoredRequest,
    ResumeVersionListResponse,
    ResumeVersionRecord,
    ResumeVersionStatusUpdateRequest,
    TailoredResumeGenerateResponse,
)
from app.models.system import DemoSeedResponse, SystemHealthCheckResponse
from app.automation.form_filler import PlaywrightFormFiller
from app.services.ats_analyzer import ATSAnalyzer
from app.services.apply_assistant import ApplyAssistantService
from app.services.apply_questions import ApplyQuestionService
from app.services.analytics import AnalyticsService, get_analytics_service
from app.services.cover_letter_generator import CoverLetterGenerator
from app.services.fit_scorer import FitScorer
from app.services.job_discovery import JobDiscoveryService
from app.services.job_url_parser import JobURLParser
from app.services.job_queue_service import JobQueueService
from app.services.jd_parser import JDParser
from app.services.outreach import OutreachService
from app.services.resume_tailor import ResumeTailor
from app.services.system import SystemService, get_system_service
from app.services.tailored_resume_service import TailoredResumeService

router = APIRouter()


def get_job_queue_service(
    queue_repo: DiscoveryQueueRepository = Depends(get_discovery_queue_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
    profile: ProfileBundle = Depends(get_profile_bundle),
    settings: Settings = Depends(get_settings),
) -> JobQueueService:
    return JobQueueService(queue_repo, application_repo, profile, settings)


def get_tailored_resume_service(
    profile: ProfileBundle = Depends(get_profile_bundle),
    queue_repo: DiscoveryQueueRepository = Depends(get_discovery_queue_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
    resume_repo: ResumeVersionRepository = Depends(get_resume_version_repository),
) -> TailoredResumeService:
    return TailoredResumeService(profile, queue_repo, application_repo, resume_repo)


def get_apply_assistant_service(
    profile: ProfileBundle = Depends(get_profile_bundle),
    session_repo: ApplySessionRepository = Depends(get_apply_session_repository),
    queue_repo: DiscoveryQueueRepository = Depends(get_discovery_queue_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
    resume_repo: ResumeVersionRepository = Depends(get_resume_version_repository),
) -> ApplyAssistantService:
    return ApplyAssistantService(profile, session_repo, queue_repo, application_repo, resume_repo)


def get_apply_question_service(
    profile: ProfileBundle = Depends(get_profile_bundle),
    session_repo: ApplySessionRepository = Depends(get_apply_session_repository),
    question_repo: ApplyQuestionRepository = Depends(get_apply_question_repository),
    queue_repo: DiscoveryQueueRepository = Depends(get_discovery_queue_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
) -> ApplyQuestionService:
    return ApplyQuestionService(profile, session_repo, question_repo, queue_repo, application_repo)


def get_outreach_service(
    profile: ProfileBundle = Depends(get_profile_bundle),
    queue_repo: DiscoveryQueueRepository = Depends(get_discovery_queue_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
) -> OutreachService:
    return OutreachService(profile, queue_repo, application_repo)


@router.post("/jobs/search", response_model=JobSearchResponse)
def search_jobs(
    payload: JobSearchRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
    settings: Settings = Depends(get_settings),
) -> JobSearchResponse:
    return JobDiscoveryService(settings, FitScorer(profile)).search(payload)


@router.post("/jobs/discover", response_model=JobDiscoverResponse)
def discover_jobs(
    payload: JobDiscoverRequest,
    service: JobQueueService = Depends(get_job_queue_service),
) -> JobDiscoverResponse:
    return service.discover(payload)


@router.get("/jobs/queue", response_model=DiscoveredJobListResponse)
def list_job_queue(
    status: QueueStatus | None = None,
    source: str | None = None,
    min_fit_score: int | None = None,
    location: str | None = None,
    work_mode: str | None = None,
    search: str | None = None,
    discovered_from: date | None = None,
    discovered_to: date | None = None,
    service: JobQueueService = Depends(get_job_queue_service),
) -> DiscoveredJobListResponse:
    return service.list_discovered_jobs(
        JobQueueFilters(
            status=status,
            source=source,
            min_fit_score=min_fit_score,
            location=location,
            work_mode=work_mode,
            search=search,
            discovered_from=discovered_from,
            discovered_to=discovered_to,
        )
    )


@router.post("/jobs/queue", response_model=DiscoveredJobRecord)
def save_job_to_queue(
    payload: DiscoveredJobSaveRequest,
    service: JobQueueService = Depends(get_job_queue_service),
) -> DiscoveredJobRecord:
    return service.save_discovered_job(payload).job


@router.post("/jobs/parse-url", response_model=JobParseUrlResponse)
def parse_job_url(payload: JobParseUrlRequest) -> JobParseUrlResponse:
    try:
        return JobURLParser().parse(str(payload.job_url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/jobs/queue/{job_id}/status", response_model=DiscoveredJobRecord)
def update_job_queue_status(
    job_id: int,
    payload: QueueStatusUpdateRequest,
    service: JobQueueService = Depends(get_job_queue_service),
) -> DiscoveredJobRecord:
    try:
        return service.update_queue_status(job_id, payload.queue_status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/queue/{job_id}/shortlist", response_model=DiscoveredJobRecord)
def shortlist_job(
    job_id: int,
    service: JobQueueService = Depends(get_job_queue_service),
) -> DiscoveredJobRecord:
    try:
        return service.shortlist_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/queue/{job_id}/skip", response_model=DiscoveredJobRecord)
def skip_job(
    job_id: int,
    service: JobQueueService = Depends(get_job_queue_service),
) -> DiscoveredJobRecord:
    try:
        return service.skip_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/queue/{job_id}/convert-to-application", response_model=DiscoveredJobRecord)
def convert_job_to_application(
    job_id: int,
    service: JobQueueService = Depends(get_job_queue_service),
) -> DiscoveredJobRecord:
    try:
        return service.convert_to_application(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/analyze", response_model=JobAnalyzeResponse)
def analyze_job(payload: JobAnalyzeRequest) -> JobAnalyzeResponse:
    parsed = JDParser().parse(payload)
    return JobAnalyzeResponse(job=parsed)


@router.post("/ats/analyze", response_model=ATSAnalyzeResponse)
def analyze_ats(
    payload: ATSAnalyzeRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
    queue_repo: DiscoveryQueueRepository = Depends(get_discovery_queue_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
) -> ATSAnalyzeResponse:
    try:
        return ATSAnalyzer(profile, queue_repo, application_repo).analyze(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ats/gap-action-plan", response_model=GapActionPlanResponse)
def gap_action_plan(
    payload: GapActionPlanRequest,
    profile: ProfileBundle = Depends(get_profile_bundle),
    queue_repo: DiscoveryQueueRepository = Depends(get_discovery_queue_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
) -> GapActionPlanResponse:
    analyzer = ATSAnalyzer(profile, queue_repo, application_repo)
    if payload.missing_keywords:
        items = analyzer.gap_action_plan(payload.missing_keywords)
    else:
        items = analyzer.analyze(
            ATSAnalyzeRequest(job=payload.job, job_queue_id=payload.job_queue_id, application_id=payload.application_id)
        ).missing_keyword_action_plan
    return GapActionPlanResponse(
        items=items,
        safe_phrasing_suggestions=analyzer._safe_phrasing_suggestions(items),
        profile_update_suggestions=analyzer._profile_update_suggestions(items),
    )


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


@router.post("/resumes/generate-tailored", response_model=TailoredResumeGenerateResponse)
def generate_tailored_resume(
    payload: ResumeGenerateTailoredRequest,
    service: TailoredResumeService = Depends(get_tailored_resume_service),
) -> TailoredResumeGenerateResponse:
    try:
        return service.generate_tailored(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/resumes/versions", response_model=ResumeVersionListResponse)
def list_resume_versions(
    repo: ResumeVersionRepository = Depends(get_resume_version_repository),
) -> ResumeVersionListResponse:
    return repo.list_versions()


@router.get("/resumes/versions/{version_id}", response_model=ResumeVersionRecord)
def get_resume_version(
    version_id: int,
    repo: ResumeVersionRepository = Depends(get_resume_version_repository),
) -> ResumeVersionRecord:
    try:
        return repo.get(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/resumes/versions/{version_id}/status", response_model=ResumeVersionRecord)
def update_resume_version_status(
    version_id: int,
    payload: ResumeVersionStatusUpdateRequest,
    repo: ResumeVersionRepository = Depends(get_resume_version_repository),
) -> ResumeVersionRecord:
    try:
        return repo.update_status(version_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/resumes/versions/{version_id}/select", response_model=ResumeVersionRecord)
def select_resume_version(
    version_id: int,
    repo: ResumeVersionRepository = Depends(get_resume_version_repository),
) -> ResumeVersionRecord:
    try:
        return repo.select(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/apply/sessions", response_model=ApplySessionCreateResponse)
def create_apply_session(
    payload: ApplySessionCreateRequest,
    service: ApplyAssistantService = Depends(get_apply_assistant_service),
) -> ApplySessionCreateResponse:
    try:
        return service.create_apply_session(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/apply/sessions/{session_id}/run-until-review", response_model=ApplySessionRecord)
async def run_apply_session_until_review(
    session_id: int,
    service: ApplyAssistantService = Depends(get_apply_assistant_service),
) -> ApplySessionRecord:
    try:
        return await service.run_until_review(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/apply/sessions", response_model=ApplySessionListResponse)
def list_apply_sessions(
    service: ApplyAssistantService = Depends(get_apply_assistant_service),
) -> ApplySessionListResponse:
    return service.list_apply_sessions()


@router.get("/apply/sessions/{session_id}", response_model=ApplySessionRecord)
def get_apply_session(
    session_id: int,
    service: ApplyAssistantService = Depends(get_apply_assistant_service),
) -> ApplySessionRecord:
    try:
        return service.get_apply_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/apply/sessions/{session_id}/questions", response_model=ApplySessionQuestionListResponse)
def list_apply_session_questions(
    session_id: int,
    service: ApplyQuestionService = Depends(get_apply_question_service),
) -> ApplySessionQuestionListResponse:
    return service.list_questions(session_id)


@router.post("/apply/sessions/{session_id}/questions/generate", response_model=ApplySessionQuestionListResponse)
def generate_apply_session_questions(
    session_id: int,
    service: ApplyQuestionService = Depends(get_apply_question_service),
) -> ApplySessionQuestionListResponse:
    try:
        return service.generate_questions(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/apply/questions/{question_id}", response_model=ApplySessionQuestionRecord)
def update_apply_question(
    question_id: int,
    payload: ApplyQuestionUpdateRequest,
    service: ApplyQuestionService = Depends(get_apply_question_service),
) -> ApplySessionQuestionRecord:
    try:
        return service.update_question(question_id, payload.answer_text, payload.requires_manual_review)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/apply/sessions/{session_id}/review-pack", response_model=ApplySessionReviewPack)
def get_apply_session_review_pack(
    session_id: int,
    service: ApplyQuestionService = Depends(get_apply_question_service),
) -> ApplySessionReviewPack:
    try:
        return service.review_pack(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/apply/sessions/{session_id}/mark-submitted-manually", response_model=ApplySessionRecord)
def mark_apply_session_submitted_manually(
    session_id: int,
    service: ApplyQuestionService = Depends(get_apply_question_service),
) -> ApplySessionRecord:
    try:
        return service.mark_submitted_manually(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/apply/sessions/{session_id}/completed-manually", response_model=ApplySessionRecord)
def mark_apply_session_completed_manually(
    session_id: int,
    payload: ApplySessionStatusUpdateRequest,
    service: ApplyAssistantService = Depends(get_apply_assistant_service),
) -> ApplySessionRecord:
    try:
        return service.mark_completed_manually(session_id, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/apply/sessions/{session_id}/failed", response_model=ApplySessionRecord)
def mark_apply_session_failed(
    session_id: int,
    payload: ApplySessionStatusUpdateRequest,
    service: ApplyAssistantService = Depends(get_apply_assistant_service),
) -> ApplySessionRecord:
    try:
        return service.mark_failed(session_id, payload.message or "User marked this apply session failed.")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@router.post("/applications", response_model=ApplicationSaveResponse)
def create_application(
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


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsOverviewResponse:
    return service.overview()


@router.get("/analytics/skills-gaps", response_model=SkillGapsResponse)
def analytics_skill_gaps(
    service: AnalyticsService = Depends(get_analytics_service),
) -> SkillGapsResponse:
    return service.skill_gaps()


@router.get("/analytics/resume-performance", response_model=ResumePerformanceResponse)
def analytics_resume_performance(
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResumePerformanceResponse:
    return service.resume_performance()


@router.get("/analytics/outreach-performance", response_model=OutreachPerformanceResponse)
def analytics_outreach_performance(
    service: AnalyticsService = Depends(get_analytics_service),
) -> OutreachPerformanceResponse:
    return service.outreach_performance()


@router.get("/analytics/weekly-insights", response_model=WeeklyInsightsResponse)
def analytics_weekly_insights(
    service: AnalyticsService = Depends(get_analytics_service),
) -> WeeklyInsightsResponse:
    return service.weekly_insights()


@router.get("/analytics/recommendations", response_model=RecommendationsResponse)
def analytics_recommendations(
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecommendationsResponse:
    return service.recommendations()


@router.get("/system/health-check", response_model=SystemHealthCheckResponse)
def system_health_check(
    service: SystemService = Depends(get_system_service),
) -> SystemHealthCheckResponse:
    return service.health_check()


@router.post("/system/seed-demo-data", response_model=DemoSeedResponse)
def seed_demo_data(
    service: SystemService = Depends(get_system_service),
) -> DemoSeedResponse:
    return service.seed_demo_data()


@router.get("/dashboard/daily-target", response_model=DailyTargetStatsResponse)
def daily_target_stats(
    service: JobQueueService = Depends(get_job_queue_service),
) -> DailyTargetStatsResponse:
    return service.get_daily_target_stats()


@router.post("/outreach/contacts", response_model=OutreachContactRecord)
def create_outreach_contact(
    payload: OutreachContactCreate,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachContactRecord:
    return repo.create_contact(payload)


@router.get("/outreach/contacts", response_model=OutreachContactListResponse)
def list_outreach_contacts(
    company: str | None = None,
    include_archived: bool = False,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachContactListResponse:
    return repo.list_contacts(company=company, include_archived=include_archived)


@router.patch("/outreach/contacts/{contact_id}", response_model=OutreachContactRecord)
def update_outreach_contact(
    contact_id: int,
    payload: OutreachContactUpdate,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachContactRecord:
    try:
        if payload.archived is True:
            return repo.archive_contact(contact_id)
        return repo.update_contact(contact_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/outreach/search-suggestions", response_model=OutreachSearchSuggestionResponse)
def outreach_search_suggestions(
    payload: OutreachSearchSuggestionRequest,
    service: OutreachService = Depends(get_outreach_service),
) -> OutreachSearchSuggestionResponse:
    return service.search_suggestions(payload)


@router.post("/outreach/messages/generate", response_model=OutreachMessageGenerateResponse)
def generate_outreach_message(
    payload: OutreachMessageGenerateRequest,
    service: OutreachService = Depends(get_outreach_service),
) -> OutreachMessageGenerateResponse:
    return service.generate_message(payload)


@router.post("/outreach/messages/follow-up", response_model=OutreachMessageGenerateResponse)
def generate_outreach_follow_up_message(
    payload: OutreachFollowUpMessageRequest,
    service: OutreachService = Depends(get_outreach_service),
) -> OutreachMessageGenerateResponse:
    return service.generate_follow_up(payload)


@router.post("/outreach/records", response_model=OutreachRecordRecord)
def create_outreach_record(
    payload: OutreachRecordCreate,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachRecordRecord:
    return repo.create_record(payload)


@router.get("/outreach/records", response_model=OutreachRecordListResponse)
def list_outreach_records(
    status: OutreachStatus | None = None,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachRecordListResponse:
    return repo.list_records(status=status)


@router.get("/outreach/dashboard", response_model=OutreachDashboardResponse)
def outreach_dashboard(
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachDashboardResponse:
    return repo.dashboard()


@router.get("/outreach/follow-ups", response_model=OutreachHistoryResponse)
def outreach_follow_ups(
    due_today: bool = False,
    overdue: bool = False,
    upcoming: bool = False,
    company: str | None = None,
    channel: OutreachChannel | None = None,
    status: OutreachStatus | None = None,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachHistoryResponse:
    return repo.follow_ups(
        due_today=due_today,
        overdue=overdue,
        upcoming=upcoming,
        company=company,
        channel=channel,
        status=status,
    )


@router.get("/outreach/history", response_model=OutreachHistoryResponse)
def outreach_history(
    contact_id: int | None = None,
    company: str | None = None,
    application_id: int | None = None,
    job_queue_id: int | None = None,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachHistoryResponse:
    return repo.history(
        contact_id=contact_id,
        company=company,
        application_id=application_id,
        job_queue_id=job_queue_id,
    )


@router.patch("/outreach/records/{record_id}/status", response_model=OutreachRecordRecord)
def update_outreach_record_status(
    record_id: int,
    payload: OutreachRecordStatusUpdate,
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachRecordRecord:
    try:
        return repo.update_record_status(record_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
