# Manual Testing Checklist

Run these checks locally before using the app for a daily job hunt.

## 1. Setup Readiness

1. Start the backend and frontend.
2. Open the dashboard.
3. Click **Check Setup**.
4. Confirm database, config, and artifacts are healthy.
5. Review warnings for Playwright or LLM configuration.

## 2. Job Discovery

1. Use **Job Discovery** with source `manual`.
2. Add a harmless test URL such as `https://example.com/job`.
3. Confirm the job is saved to the discovery queue.
4. Use `remoteok` only when network access is available.
5. Confirm RemoteOK errors are shown as readable source errors.

## 3. Queue Filters

1. Filter by status, source, min fit, location, work mode, and search.
2. Confirm filters can be combined.
3. Click **Clear** and confirm the queue resets.

## 4. ATS Analysis

1. Pick a queue job.
2. Click **ATS**.
3. Confirm score, matched keywords, missing keywords, warnings, and gap plan appear.
4. Confirm missing skills are not inserted as claimed experience.

## 5. Resume Generation

1. Click **Resume** on a queue job.
2. Confirm a resume version appears.
3. Mark it reviewed, selected, and archived.
4. Confirm only reviewed/selected status changes happen; no application is submitted.

## 6. Apply Assistant

1. Start Apply Assist from a queue job with a URL.
2. Confirm the session is created.
3. Run until review only on a safe test page.
4. Confirm the final submit remains manual.
5. Generate questions and review/edit answers.
6. Mark submitted manually only after you personally submit outside automation.

## 7. Outreach

1. Add a contact manually.
2. Generate manual search suggestions.
3. Confirm guessed emails are marked low confidence.
4. Generate a LinkedIn or email draft.
5. Copy the message manually.
6. Save an outreach record and update status manually.

## 8. Follow-Up

1. Create or seed outreach records with follow-up dates.
2. Review due today, overdue, and upcoming follow-up queues.
3. Generate a follow-up draft.
4. Confirm no email or LinkedIn message is sent by the app.

## 9. Analytics Dashboard

1. Seed demo data if needed.
2. Review funnel, ATS distribution, sources, resume usage, missing skills, and outreach charts.
3. Confirm weekly insights mention small sample size when data is limited.
4. Confirm recommendations are based only on local tracked data.
