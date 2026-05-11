from app.core.config_loader import ProfileBundle
from app.db.apply_question_repository import ApplyQuestionRepository
from app.db.apply_session_repository import ApplySessionRepository
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.models.apply_session import (
    ApplySessionQuestionListResponse,
    ApplySessionQuestionRecord,
    ApplySessionReviewPack,
)


QUESTION_PATTERNS = [
    ("notice period", "Notice Period"),
    ("expected salary", "Expected Salary"),
    ("ctc", "Compensation"),
    ("years of experience", "Years of Experience"),
    ("work authorization", "Work Authorization"),
    ("relocation", "Relocation"),
    ("remote", "Remote Preference"),
    ("hybrid", "Hybrid Preference"),
    ("portfolio", "Portfolio"),
    ("github", "GitHub URL"),
    ("linkedin", "LinkedIn URL"),
    ("why are you interested", "Why Interested"),
    ("why should we hire you", "Why Hire"),
    ("relevant experience", "Relevant Experience"),
    ("cover letter", "Cover Letter"),
    ("additional notes", "Additional Notes"),
]


class ApplyQuestionService:
    def __init__(
        self,
        profile_bundle: ProfileBundle,
        session_repository: ApplySessionRepository,
        question_repository: ApplyQuestionRepository,
        queue_repository: DiscoveryQueueRepository,
        application_repository: ApplicationRepository,
    ):
        self.profile_bundle = profile_bundle
        self.session_repository = session_repository
        self.question_repository = question_repository
        self.queue_repository = queue_repository
        self.application_repository = application_repository

    def generate_questions(self, session_id: int) -> ApplySessionQuestionListResponse:
        session = self.session_repository.get(session_id)
        existing = self.question_repository.list_for_session(session_id).questions
        seen = {question.question_text.lower() for question in existing}
        candidates = self._candidate_questions(session)
        created: list[ApplySessionQuestionRecord] = []
        for question_text, label in candidates:
            if question_text.lower() in seen:
                continue
            answer_text, confidence, source, manual = self._answer(question_text, session)
            created.append(
                self.question_repository.create(
                    apply_session_id=session.id,
                    question_text=question_text,
                    detected_field_label=label,
                    answer_text=answer_text,
                    confidence_score=confidence,
                    answer_source=source,
                    requires_manual_review=manual,
                )
            )
        return ApplySessionQuestionListResponse(questions=[*existing, *created])

    def list_questions(self, session_id: int) -> ApplySessionQuestionListResponse:
        return self.question_repository.list_for_session(session_id)

    def update_question(self, question_id: int, answer_text: str | None, requires_manual_review: bool | None) -> ApplySessionQuestionRecord:
        return self.question_repository.update(question_id, answer_text, requires_manual_review)

    def review_pack(self, session_id: int) -> ApplySessionReviewPack:
        session = self.session_repository.get(session_id)
        questions = self.question_repository.list_for_session(session_id).questions
        unanswered = [question for question in questions if question.requires_manual_review or not question.answer_text]
        generated = [question for question in questions if question.answer_text]
        warnings = list(session.errors)
        if unanswered:
            warnings.append("Some questions require manual review before submitting.")
        if not session.resume_file_path:
            warnings.append("No resume file is attached in this session.")
        return ApplySessionReviewPack(
            session=session,
            selected_resume_version=session.resume_version_id,
            resume_file_path=session.resume_file_path,
            cover_letter=session.cover_letter_text,
            field_fill_summary=session.fill_summary,
            unanswered_questions=unanswered,
            generated_answers=generated,
            warnings=warnings,
            screenshots=session.screenshot_paths,
            final_manual_checklist=[
                "Resume attached or uploaded manually.",
                "Cover letter checked.",
                "Required fields reviewed.",
                "User clicked submit manually only after review.",
            ],
        )

    def mark_submitted_manually(self, session_id: int):
        from app.models.application import ApplicationStatus, ApplicationStatusUpdateRequest
        from app.models.apply_session import ApplySessionStatus
        from app.models.job_queue import QueueStatus

        session = self.session_repository.update(
            session_id,
            status=ApplySessionStatus.COMPLETED_MANUALLY,
            fill_summary="User confirmed they submitted manually after review.",
        )
        if session.job_queue_id is not None:
            self.queue_repository.update_queue_status(session.job_queue_id, QueueStatus.APPLIED)
        if session.application_id is not None:
            self.application_repository.update_status(
                session.application_id,
                ApplicationStatusUpdateRequest(status=ApplicationStatus.SUBMITTED, notes="Submitted manually by user after apply assistant review."),
            )
        return session

    def _candidate_questions(self, session) -> list[tuple[str, str]]:
        text_parts = [session.fill_summary or "", session.cover_letter_text or ""]
        text_parts.extend(result.label for result in session.field_results)
        text = " ".join(text_parts).lower()
        candidates = [
            ("What is your notice period?", "Notice Period"),
            ("What are your expected salary or compensation expectations?", "Expected Salary"),
            ("Are you authorized to work for this role?", "Work Authorization"),
            ("Are you open to relocation or remote-first work?", "Relocation"),
            ("Why are you interested in this role?", "Why Interested"),
            ("Describe your relevant experience for this role.", "Relevant Experience"),
            ("Cover letter or additional notes", "Cover Letter"),
        ]
        for pattern, label in QUESTION_PATTERNS:
            if pattern in text:
                question = f"{label}: {pattern}"
                candidates.append((question, label))
        return candidates

    def _answer(self, question_text: str, session) -> tuple[str | None, float, str, bool]:
        lower = question_text.lower()
        profile = self.profile_bundle.profile
        prefs = self.profile_bundle.preferences
        answers = self.profile_bundle.answers
        if "notice" in lower and answers.notice_period:
            return answers.notice_period, 0.95, "answers_yaml", False
        if ("salary" in lower or "ctc" in lower or "compensation" in lower) and answers.salary_expectation:
            return answers.salary_expectation, 0.9, "answers_yaml", False
        if "authorization" in lower and answers.work_authorization:
            return answers.work_authorization, 0.95, "answers_yaml", False
        if "relocation" in lower:
            value = answers.custom.get("relocation") or ("Open to remote-first roles." if prefs.remote else None)
            return (value, 0.85, "answers_yaml" if answers.custom.get("relocation") else "preferences", False) if value else (None, 0.0, "manual_required", True)
        if "remote" in lower or "hybrid" in lower:
            return ("Prefer remote-first roles; open to discussion based on role fit." if prefs.remote else "Open to discussing work mode.", 0.8, "preferences", False)
        if "github" in lower and profile.github:
            return profile.github, 0.95, "profile", False
        if "linkedin" in lower and profile.linkedin:
            return profile.linkedin, 0.95, "profile", False
        if "portfolio" in lower:
            return None, 0.0, "manual_required", True
        if "years of experience" in lower or "current ctc" in lower:
            return None, 0.0, "manual_required", True
        if "why are you interested" in lower:
            return f"I am interested in the {session.title} role at {session.company} because it aligns with my verified experience in {', '.join(profile.skills[:5])}.", 0.7, "generated", True
        if "why should we hire" in lower or "relevant experience" in lower:
            return f"My relevant experience includes {profile.summary} I would keep the final wording grounded in the resume and profile data before submitting.", 0.7, "generated", True
        if "cover letter" in lower or "additional notes" in lower:
            return session.cover_letter_text, 0.8 if session.cover_letter_text else 0.0, "generated" if session.cover_letter_text else "manual_required", not bool(session.cover_letter_text)
        return None, 0.0, "manual_required", True
