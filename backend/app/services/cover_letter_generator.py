from app.core.config_loader import ProfileBundle
from app.models.cover_letter import CoverLetterRequest, CoverLetterResponse


class CoverLetterGenerator:
    def __init__(self, profile_bundle: ProfileBundle):
        self.profile_bundle = profile_bundle

    def generate(self, payload: CoverLetterRequest) -> CoverLetterResponse:
        profile = self.profile_bundle.profile
        job = payload.job
        matched_skills = [skill for skill in profile.skills if skill.lower() in {item.lower() for item in job.required_skills}]
        top_experience = profile.experience[0] if profile.experience else None

        experience_sentence = ""
        if top_experience:
            experience_sentence = (
                f"In my role as {top_experience.title} at {top_experience.company}, "
                f"I worked on {', '.join(top_experience.skills[:4])}."
            )

        letter = "\n\n".join(
            [
                f"Dear {job.company} hiring team,",
                (
                    f"I am excited to apply for the {job.title} role. "
                    f"My background aligns with your needs around {', '.join(matched_skills[:6]) if matched_skills else 'the core responsibilities described in the posting'}."
                ),
                experience_sentence or profile.summary,
                (
                    "I would welcome the chance to discuss how my experience can help your team. "
                    "I have kept this letter grounded only in the verified profile information available to this assistant."
                ),
                f"Sincerely,\n{profile.name}",
            ]
        )

        return CoverLetterResponse(
            cover_letter=letter,
            cautions=[
                "Review before use; Phase 1 never submits automatically.",
                "No unsupported accomplishments were added.",
            ],
        )
