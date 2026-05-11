# Privacy And Safety

This app is a local-first job hunt assistant. It is not designed for hosted multi-user deployment yet.

## Human Approval

- The app must not auto-submit job applications.
- The Apply Assistant can prepare and fill fields for review.
- Final submission is always performed manually by the user.

## Outreach Safety

- The app does not send emails.
- The app does not send LinkedIn messages.
- The app does not automate LinkedIn.
- Search suggestions are strings for the user to open manually.
- Guessed email patterns are low confidence and must be verified manually.

## Scraping

- Private data scraping is not part of this app.
- LinkedIn, Naukri, and Wellfound automation remain disabled unless a future explicit, compliant integration is designed.
- The manual URL parser only fetches pages after the user explicitly requests it.
- The parser does not use credentials or cookies.

## Local Data

- Application data is stored in local SQLite.
- The default database path is `data/jobhunt.db`.
- Generated resumes, DOCX/PDF files, and screenshots are stored under `backend/artifacts`.
- These files may contain resume, profile, contact, and application data.

## API Keys

- Put API keys in `.env`, not in source files.
- `.env.example` should contain placeholder values only.
- If no OpenAI-compatible key is configured, local fallback behavior should remain active.

## YAML Profile Safety

- `profile.yaml`, `preferences.yaml`, and `answers.yaml` may contain sensitive personal information.
- Keep them local.
- Do not commit real phone numbers, addresses, salary details, or private answers unless this repository is private and intentionally used that way.

## Demo Data

- Demo seed data uses fake companies and fake local URLs.
- Demo data is for testing analytics and UI flows only.
