# Local Runbook

This app is intended for local use only.

## Backend Setup

```powershell
cd C:\Users\NEW\job_assistant\Automation_AI
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## Frontend Setup

```powershell
cd C:\Users\NEW\job_assistant\Automation_AI\frontend
npm install
```

## Start Backend

```powershell
cd C:\Users\NEW\job_assistant\Automation_AI\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## Start Frontend

```powershell
cd C:\Users\NEW\job_assistant\Automation_AI\frontend
npm.cmd run dev
```

Open `http://localhost:3000`.

## If Port 8000 Is Busy

Find the process:

```powershell
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
Get-Process -Id <PID>
```

Stop it only if it is your local dev server:

```powershell
Stop-Process -Id <PID>
```

Or run the backend on another port and set:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8001"
```

## Install Playwright Browsers

```powershell
backend\.venv\Scripts\python.exe -m playwright install chromium
```

## Run Tests

```powershell
python -m compileall backend/app
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm.cmd run build
npm.cmd run lint
```

## Smoke Test

Start the backend first, then:

```powershell
python scripts\smoke_test.py
```

Use another API base if needed:

```powershell
$env:JOB_ASSISTANT_API_BASE="http://localhost:8001"
python scripts\smoke_test.py
```

## Reset Local Database

The default database is `data/jobhunt.db`.

Stop the backend first. Then move or delete the database file:

```powershell
Move-Item data\jobhunt.db data\jobhunt.backup.db
```

Restart the backend to recreate schema.

## Generated Artifacts

Generated resumes and apply-session screenshots live under:

- `backend/artifacts/resumes`
- `backend/artifacts/apply_sessions`

These files can contain personal information. Do not commit them.
