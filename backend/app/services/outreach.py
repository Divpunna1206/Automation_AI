from urllib.parse import urlsplit

from app.core.config_loader import ProfileBundle
from app.db.discovery_queue_repository import DiscoveryQueueRepository
from app.db.repository import ApplicationRepository
from app.models.outreach import (
    EmailPatternGuess,
    OutreachFollowUpMessageRequest,
    OutreachMessageGenerateRequest,
    OutreachMessageGenerateResponse,
    OutreachMessageType,
    OutreachSearchSuggestionRequest,
    OutreachSearchSuggestionResponse,
)


class OutreachService:
    def __init__(
        self,
        profile_bundle: ProfileBundle,
        queue_repository: DiscoveryQueueRepository,
        application_repository: ApplicationRepository,
    ):
        self.profile_bundle = profile_bundle
        self.queue_repository = queue_repository
        self.application_repository = application_repository

    def search_suggestions(self, payload: OutreachSearchSuggestionRequest) -> OutreachSearchSuggestionResponse:
        company = payload.company.strip()
        role = payload.role_title or "hiring manager"
        domain = self._domain_from_url(payload.job_url)
        queries = [
            f'site:linkedin.com/in "{company}" recruiter',
            f'site:linkedin.com/in "{company}" talent acquisition',
            f'site:linkedin.com/in "{company}" hiring manager "{role}"',
        ]
        patterns = []
        if domain:
            patterns = [
                EmailPatternGuess(pattern="firstname.lastname", example=f"firstname.lastname@{domain}", confidence_score=0.2, warning="Guessed pattern only; verify manually before use."),
                EmailPatternGuess(pattern="first", example=f"first@{domain}", confidence_score=0.15, warning="Guessed pattern only; verify manually before use."),
                EmailPatternGuess(pattern="firstlast", example=f"firstlast@{domain}", confidence_score=0.15, warning="Guessed pattern only; verify manually before use."),
            ]
        return OutreachSearchSuggestionResponse(
            search_queries=queries,
            company_domain=domain,
            guessed_email_patterns=patterns,
            warnings=[
                "Open these searches manually; this assistant does not scrape private data.",
                "Guessed emails are low confidence and must be verified before manual outreach.",
            ],
        )

    def generate_message(self, payload: OutreachMessageGenerateRequest) -> OutreachMessageGenerateResponse:
        profile = self.profile_bundle.profile
        role_title = payload.role_title
        company = payload.company
        contact = payload.contact_name or "there"
        points = self._strong_points()
        point_text = ", ".join(points[:3]) if points else profile.summary

        if payload.message_type in {OutreachMessageType.FOLLOW_UP_1, OutreachMessageType.FOLLOW_UP_2}:
            message = (
                f"Hi {contact}, I wanted to follow up on my application for the {role_title} role at {company}. "
                f"My background includes {point_text}. I would be grateful if you could point me to the right person or share any next steps. Thanks!"
            )
        elif payload.channel.value == "email":
            message = (
                f"Hi {contact},\n\nI recently applied for the {role_title} role at {company}. "
                f"My experience includes {point_text}, and I am especially interested in contributing to this team. "
                "If useful, I would be happy to share more context or clarify fit.\n\n"
                f"Best,\n{profile.name}"
            )
        else:
            message = (
                f"Hi {contact}, I applied for the {role_title} role at {company}. "
                f"My background includes {point_text}. I would appreciate connecting and learning whether my profile may be relevant."
            )
        return OutreachMessageGenerateResponse(
            message_text=message,
            warnings=[
                "Review before sending manually.",
                "No referral, interview, unsupported metric, or unverified experience was claimed.",
            ],
            strongest_relevant_points=points,
        )

    def generate_follow_up(self, payload: OutreachFollowUpMessageRequest) -> OutreachMessageGenerateResponse:
        profile = self.profile_bundle.profile
        contact = payload.contact_name or "there"
        days = max(payload.days_since_first_message, 0)
        timing = f"{days} days ago" if days else "recently"
        context = self._trim_sentence(payload.original_message)
        if payload.channel.value == "email":
            message = (
                f"Hi {contact},\n\nI applied for the {payload.role_title} role at {payload.company} {timing} "
                "and wanted to share a brief follow-up. "
                f"My original note focused on {context}. "
                "I remain interested in the role and would be grateful for any guidance on whether my profile is relevant.\n\n"
                f"Best,\n{profile.name}"
            )
        else:
            message = (
                f"Hi {contact}, I applied for the {payload.role_title} role at {payload.company} {timing}. "
                f"My original note focused on {context}. I remain interested and would appreciate any guidance on fit or next steps."
            )
        return OutreachMessageGenerateResponse(
            message_text=message,
            warnings=[
                "Review before copying and sending manually.",
                "No referral, interview, urgency claim, or unverified experience was claimed.",
            ],
            strongest_relevant_points=self._strong_points(),
        )

    def _strong_points(self) -> list[str]:
        profile = self.profile_bundle.profile
        points = []
        if profile.skills:
            points.append("verified skills in " + ", ".join(profile.skills[:5]))
        for item in profile.experience[:2]:
            if item.highlights:
                points.append(item.highlights[0])
        return points[:4]

    def _trim_sentence(self, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            return "my relevant background"
        return cleaned[:180].rstrip(" ,.;:") or "my relevant background"

    def _domain_from_url(self, job_url: str | None) -> str | None:
        if not job_url:
            return None
        host = urlsplit(job_url).netloc.lower().removeprefix("www.")
        if not host:
            return None
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host
