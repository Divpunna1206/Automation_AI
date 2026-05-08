# Backend

FastAPI service for the Phase 1 Agentic Job Hunt Pipeline.

## Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. OpenAPI docs are at `/docs`.

## Test

```powershell
pytest
```

## Phase 2 Notes

`/forms/fill` opens Playwright and pauses for user review. The backend intentionally does not submit applications.
