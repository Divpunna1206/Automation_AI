from app.core.config_loader import ProfileBundle
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.db.resume_version_repository import ResumeVersionRepository
from app.models.ats import ATSAnalyzeRequest
from app.models.resume import ResumeGenerateRequest, ResumeGenerateTailoredRequest, TailoredResumeGenerateResponse
from app.services.ats_analyzer import ATSAnalyzer
from app.services.resume_tailor import ResumeTailor


class TailoredResumeService:
    def __init__(
        self,
        profile_bundle: ProfileBundle,
        queue_repository: DiscoveryQueueRepository,
        application_repository: ApplicationRepository,
        resume_version_repository: ResumeVersionRepository,
    ):
        self.profile_bundle = profile_bundle
        self.queue_repository = queue_repository
        self.application_repository = application_repository
        self.resume_version_repository = resume_version_repository

    def generate_tailored(self, request: ResumeGenerateTailoredRequest) -> TailoredResumeGenerateResponse:
        ats = ATSAnalyzer(self.profile_bundle, self.queue_repository, self.application_repository).analyze(
            ATSAnalyzeRequest(
                job=request.job,
                title=request.title,
                company=request.company,
                description=request.description,
                job_queue_id=request.job_queue_id,
                application_id=request.application_id,
            )
        )
        resume = ResumeTailor(self.profile_bundle).generate(ResumeGenerateRequest(job=ats.job), ats=ats)
        record = self.resume_version_repository.create(
            resume_version_id=resume.resume_version,
            job_queue_id=request.job_queue_id,
            application_id=request.application_id,
            title=ats.job.title,
            company=ats.job.company,
            ats_score=ats.ats_score,
            matched_keywords=ats.matched_keywords,
            missing_keywords=ats.missing_keywords,
            file_path=resume.pdf_path,
            file_path_docx=resume.docx_path,
        )
        return TailoredResumeGenerateResponse(
            resume_markdown=resume.resume_markdown,
            resume_version=resume.resume_version,
            pdf_path=resume.pdf_path,
            docx_path=resume.docx_path,
            truthful_constraints=resume.truthful_constraints
            + ["Generated from verified profile data. Internal note: missing skills were not inserted."],
            ats=ats,
            version_record=record,
        )
