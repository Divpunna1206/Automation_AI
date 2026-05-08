from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.settings import get_settings


class ExperienceItem(BaseModel):
    company: str
    title: str
    start: str
    end: str
    highlights: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)

    @field_validator("start", "end", mode="before")
    @classmethod
    def coerce_date_label(cls, value: object) -> str:
        return str(value)


class Profile(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    summary: str
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class Preferences(BaseModel):
    target_titles: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    remote: bool = True
    min_fit_score: int = 70
    excluded_keywords: list[str] = Field(default_factory=list)
    preferred_keywords: list[str] = Field(default_factory=list)


class Answers(BaseModel):
    work_authorization: str | None = None
    sponsorship_required: str | None = None
    notice_period: str | None = None
    salary_expectation: str | None = None
    custom: dict[str, str] = Field(default_factory=dict)


class ProfileBundle(BaseModel):
    profile: Profile
    preferences: Preferences
    answers: Answers


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Missing config file: {path.name}")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"Invalid YAML object: {path.name}")
    return data


@lru_cache
def get_profile_bundle() -> ProfileBundle:
    settings = get_settings()
    return ProfileBundle(
        profile=Profile.model_validate(_load_yaml(settings.profile_path)),
        preferences=Preferences.model_validate(_load_yaml(settings.preferences_path)),
        answers=Answers.model_validate(_load_yaml(settings.answers_path)),
    )
