# Agentic Job Hunt Pipeline

Phase 1 MVP for a human-in-the-loop job application automation assistant.

## What Phase 1 Includes

- FastAPI backend with clean service boundaries.
- YAML config loading from `profile.yaml`, `preferences.yaml`, and `answers.yaml`.
- Manual job input through `POST /jobs/analyze`.
- Rule-based JD parsing and fit scoring.
- Truthful resume tailoring from profile data using Jinja2 templates.
- Cover letter generation grounded in profile data.
- SQLite application tracker table with status, resume version, cover letter, and follow-up fields.
- Next.js dashboard for analyze, score, generate, approve, skip, and save workflows.

Phase 1 intentionally does not submit applications automatically.

## Phase 2 Additions

- Job discovery via `POST /jobs/search`.
- RemoteOK integration through its public JSON feed.
- Manual job URL intake for custom review flows.
- Guarded LinkedIn, Naukri, and Wellfound adapters. These return disabled-source messages unless `ENABLE_WEB_SCRAPING=true`; add authenticated selectors/API keys and confirm site terms before production scraping.
- Fit scoring with title, skills, seniority, location, preferred keywords, and company reputation signals.
- Jinja2-grounded resume generation with versioned PDF artifacts under `backend/artifacts/resumes`.
- Playwright form-fill planning and browser automation that pauses for user review and never clicks final submit.
- Application tracker list and status update endpoints.

## Phase 2 API

- `POST /jobs/search`
- `POST /jobs/analyze`
- `POST /jobs/score`
- `POST /resumes/generate`
- `POST /cover-letter/generate`
- `POST /forms/fill-plan`
- `POST /forms/fill`
- `POST /applications/save`
- `GET /applications`
- `PATCH /applications/{application_id}/status`
- `GET /dashboard/stats`

## Run Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`.

## Test

```powershell
cd backend
pytest
```

## Architecture Notes

The backend keeps API routes thin and moves behavior into services:

- `JDParser` extracts skills, responsibilities, seniority, employment type, and risk flags.
- `FitScorer` compares parsed requirements to verified profile skills and preferences.
- `ResumeTailor` renders a tailored markdown resume without inventing missing experience.
- `CoverLetterGenerator` creates a reviewable letter grounded in profile data.
- `ApplicationRepository` owns persistence behind a repository boundary so PostgreSQL can be added later.
- `LLMProvider` supports a local deterministic fallback and an OpenAI-compatible chat completions provider.
- `ApplicationFormFiller` is a Playwright-ready boundary that can prepare fill plans but rejects auto-submit in Phase 1.
- `JobDiscoveryService` normalizes source-specific search results before parsing and scoring.

Future phases can add Playwright discovery/form-fill agents and an OpenAI-compatible LLM provider behind the existing service interfaces while preserving the approval gate.
