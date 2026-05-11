from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.config_loader import load_profile_bundle


def write_yaml(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def valid_preferences(path: Path) -> Path:
    return write_yaml(
        path,
        """
target_titles:
  - AI Engineer
target_locations:
  - Remote
remote: true
min_fit_score: 70
excluded_keywords:
  - unpaid
preferred_keywords:
  - FastAPI
""",
    )


def valid_answers(path: Path) -> Path:
    return write_yaml(
        path,
        """
work_authorization: Authorized
sponsorship_required: "No"
notice_period: Immediate
salary_expectation: Open
custom:
  relocation: Remote only
""",
    )


def test_config_loader_drops_blank_list_items(tmp_path) -> None:
    profile = write_yaml(
        tmp_path / "profile.yaml",
        """
name: Test User
email: test@example.com
summary: AI engineer
skills:
  - Python
  -
experience:
  - company: Test Co
    title: Engineer
    start: 2021
    end: Present
    skills:
      - FastAPI
      -
    highlights:
      - Built FastAPI services.
education:
  - Test University
certifications: []
""",
    )

    bundle = load_profile_bundle(
        profile,
        valid_preferences(tmp_path / "preferences.yaml"),
        valid_answers(tmp_path / "answers.yaml"),
    )

    assert bundle.profile.skills == ["Python"]
    assert bundle.profile.experience[0].skills == ["FastAPI"]


def test_config_loader_reports_exact_invalid_path(tmp_path) -> None:
    profile = write_yaml(
        tmp_path / "profile.yaml",
        """
name: Test User
email: test@example.com
summary: AI engineer
skills:
  - Python
experience:
  - company: Test Co
    title: Engineer
    start: 2021
    end: Present
    skills:
      - FastAPI
    highlights:
      - 123
education: []
certifications: []
""",
    )

    with pytest.raises(HTTPException) as exc_info:
        load_profile_bundle(
            profile,
            valid_preferences(tmp_path / "preferences.yaml"),
            valid_answers(tmp_path / "answers.yaml"),
        )

    assert exc_info.value.status_code == 500
    assert "profile.yaml.experience.0.highlights" in exc_info.value.detail
