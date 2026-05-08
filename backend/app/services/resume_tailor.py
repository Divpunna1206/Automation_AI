from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config_loader import ProfileBundle
from app.core.settings import ROOT_DIR
from app.models.resume import ResumeGenerateRequest, ResumeGenerateResponse


class ResumeTailor:
    def __init__(self, profile_bundle: ProfileBundle):
        self.profile_bundle = profile_bundle
        self.env = Environment(
            loader=FileSystemLoader(ROOT_DIR / "backend" / "app" / "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, payload: ResumeGenerateRequest) -> ResumeGenerateResponse:
        profile = self.profile_bundle.profile
        job_skills = set(payload.job.required_skills + payload.job.preferred_skills)
        truthful_skills = [skill for skill in profile.skills if skill.lower() in {item.lower() for item in job_skills}]
        highlighted_experience = []

        for item in profile.experience:
            relevant_highlights = [
                highlight for highlight in item.highlights
                if any(skill.lower() in highlight.lower() for skill in job_skills)
            ]
            highlighted_experience.append(
                {
                    **item.model_dump(),
                    "highlights": relevant_highlights or item.highlights[:3],
                }
            )

        template = self.env.get_template("resume.md.j2")
        resume_version = f"{payload.job.company.lower().replace(' ', '-')}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        resume_markdown = template.render(
            profile=profile,
            job=payload.job,
            truthful_skills=truthful_skills or profile.skills[:10],
            experience=highlighted_experience,
        )
        pdf_path = self._write_pdf(resume_version, resume_markdown)

        return ResumeGenerateResponse(
            resume_markdown=resume_markdown,
            resume_version=resume_version,
            pdf_path=str(pdf_path),
            truthful_constraints=[
                "Only skills and experience present in profile.yaml were used.",
                "Missing job requirements are not fabricated; they remain visible in scoring.",
                "PDF content is rendered from the same Jinja2-grounded resume content.",
            ],
        )

    def _write_pdf(self, resume_version: str, text: str) -> Path:
        output_dir = ROOT_DIR / "backend" / "artifacts" / "resumes"
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / f"{resume_version}.pdf"
        pdf_path.write_bytes(_minimal_pdf(text))
        return pdf_path


def _minimal_pdf(text: str) -> bytes:
    # Lightweight MVP PDF writer. The source content still comes from Jinja2.
    escaped_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:110]
        for line in text.splitlines()
    ][:55]
    content_lines = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
    for line in escaped_lines:
        content_lines.append(f"({line}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(pdf)
