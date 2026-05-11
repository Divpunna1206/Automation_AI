from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.core.settings import get_settings


def _clean_string_list(value: object, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")

    cleaned: list[str] = []
    for index, item in enumerate(value):
        if item is None:
            continue
        if not isinstance(item, str):
            raise ValueError(f"{field_name}.{index} must be a string")
        stripped = item.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


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

    @field_validator("highlights", "skills", mode="before")
    @classmethod
    def clean_experience_lists(cls, value: object, info) -> list[str]:
        return _clean_string_list(value, info.field_name)

    @model_validator(mode="after")
    def require_non_blank_strings(self) -> "ExperienceItem":
        for field_name in ("company", "title", "start", "end"):
            value = getattr(self, field_name)
            if not str(value).strip():
                raise ValueError(f"{field_name} must not be blank")
            setattr(self, field_name, str(value).strip())
        return self


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

    @field_validator("skills", "education", "certifications", mode="before")
    @classmethod
    def clean_profile_lists(cls, value: object, info) -> list[str]:
        return _clean_string_list(value, info.field_name)

    @field_validator("name", "email", "summary")
    @classmethod
    def required_profile_fields_not_blank(cls, value: str, info) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} must not be blank")
        return stripped


class Preferences(BaseModel):
    target_titles: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    remote: bool = True
    min_fit_score: int = 70
    daily_application_target: int = Field(default=25, ge=1, le=200)
    excluded_keywords: list[str] = Field(default_factory=list)
    preferred_keywords: list[str] = Field(default_factory=list)

    @field_validator("target_titles", "target_locations", "excluded_keywords", "preferred_keywords", mode="before")
    @classmethod
    def clean_preference_lists(cls, value: object, info) -> list[str]:
        return _clean_string_list(value, info.field_name)


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


def _format_validation_error(filename: str, exc: ValidationError) -> str:
    details = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        details.append(f"{filename}.{location}: {error['msg']}")
    return "Invalid configuration: " + "; ".join(details)


def load_profile_bundle(profile_path: Path, preferences_path: Path, answers_path: Path) -> ProfileBundle:
    try:
        profile = Profile.model_validate(_load_yaml(profile_path))
        preferences = Preferences.model_validate(_load_yaml(preferences_path))
        answers = Answers.model_validate(_load_yaml(answers_path))
    except ValidationError as exc:
        filename = "configuration"
        if exc.title == "Profile":
            filename = profile_path.name
        elif exc.title == "Preferences":
            filename = preferences_path.name
        elif exc.title == "Answers":
            filename = answers_path.name
        raise HTTPException(status_code=500, detail=_format_validation_error(filename, exc)) from exc
    return ProfileBundle(profile=profile, preferences=preferences, answers=answers)


def validate_config() -> ProfileBundle:
    settings = get_settings()
    return load_profile_bundle(settings.profile_path, settings.preferences_path, settings.answers_path)


@lru_cache
def get_profile_bundle() -> ProfileBundle:
    return validate_config()
