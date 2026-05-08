"use client";

import { Check, FileText, Save, Search, Send, SkipForward, WandSparkles } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type ParsedJob = {
  title: string;
  company: string;
  description: string;
  url?: string | null;
  location?: string | null;
  source: string;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  seniority?: string | null;
  employment_type?: string | null;
  risk_flags: string[];
  company_reputation?: number | null;
};

type FitScore = {
  score: number;
  recommendation: string;
  matched_skills: string[];
  missing_skills: string[];
  concerns: string[];
  rationale: string;
  signals: Record<string, number>;
};

type JobListing = {
  title: string;
  company: string;
  description: string;
  url?: string | null;
  location?: string | null;
  source: string;
  tags: string[];
  company_reputation?: number | null;
};

type ScoredJobListing = {
  listing: JobListing;
  parsed_job: ParsedJob;
  score: FitScore;
};

type ApplicationRecord = {
  id: number;
  company: string;
  title: string;
  fit_score?: number | null;
  recommendation?: string | null;
  resume_version?: string | null;
  resume_pdf_path?: string | null;
  status: string;
  follow_up_date?: string | null;
  discovered_at?: string | null;
  reviewed_at?: string | null;
  materials_generated_at?: string | null;
  approved_at?: string | null;
  form_prepared_at?: string | null;
  submitted_at?: string | null;
  interview_at?: string | null;
  rejected_at?: string | null;
  offer_at?: string | null;
  skipped_at?: string | null;
  created_at: string;
};

type DashboardStats = {
  total_jobs: number;
  average_fit_score?: number | null;
  due_follow_ups: number;
  status_counts: Record<string, number>;
  recent_applications: ApplicationRecord[];
};

type ApplicationListResponse = {
  applications: ApplicationRecord[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const APPLICATION_STATUSES = [
  "discovered",
  "reviewed",
  "materials_generated",
  "approved",
  "form_prepared",
  "submitted",
  "interview",
  "rejected",
  "offer",
  "skipped"
] as const;

const sampleDescription =
  "We are hiring a Senior Full-Stack AI Engineer to build FastAPI services, React dashboards, Playwright automations, and LLM-powered workflows. You will design human-in-the-loop review systems, work with SQL databases, and collaborate across product and engineering.";

export default function Dashboard() {
  const [title, setTitle] = useState("Senior Full-Stack AI Engineer");
  const [company, setCompany] = useState("Acme AI");
  const [location, setLocation] = useState("Remote, United States");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState(sampleDescription);
  const [job, setJob] = useState<ParsedJob | null>(null);
  const [fitScore, setFitScore] = useState<FitScore | null>(null);
  const [resume, setResume] = useState("");
  const [resumeVersion, setResumeVersion] = useState("");
  const [resumePdfPath, setResumePdfPath] = useState("");
  const [coverLetter, setCoverLetter] = useState("");
  const [searchQuery, setSearchQuery] = useState("AI Product Engineer");
  const [sources, setSources] = useState("remoteok,manual");
  const [manualUrls, setManualUrls] = useState("");
  const [searchResults, setSearchResults] = useState<ScoredJobListing[]>([]);
  const [sourceErrors, setSourceErrors] = useState<Record<string, string>>({});
  const [fillPlan, setFillPlan] = useState<string[]>([]);
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [statusDrafts, setStatusDrafts] = useState<Record<number, string>>({});
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void bootstrapDashboard();
  }, []);

  const recommendationTone = useMemo(() => {
    if (!fitScore) return "neutral";
    if (fitScore.recommendation === "approve") return "good";
    if (fitScore.recommendation === "skip") return "bad";
    return "warn";
  }, [fitScore]);

  async function api<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined
    });
    if (!response.ok) {
      const error = await response.text();
      if (response.status === 404 && error.includes('"detail":"Not Found"')) {
        throw new Error(`Backend route ${path} was not found. Restart the FastAPI server so it loads the latest API routes.`);
      }
      throw new Error(error || `Request failed: ${response.status}`);
    }
    return response.json() as Promise<T>;
  }

  async function bootstrapDashboard() {
    try {
      await Promise.all([refreshStats(), refreshApplications()]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to load dashboard data.");
    }
  }

  async function refreshStats() {
    const nextStats = await api<DashboardStats>("/dashboard/stats");
    setStats(nextStats);
  }

  async function refreshApplications() {
    const response = await api<ApplicationListResponse>("/applications");
    setApplications(response.applications);
    setStatusDrafts(
      Object.fromEntries(response.applications.map((application) => [application.id, application.status]))
    );
  }

  async function analyze(event: FormEvent) {
    event.preventDefault();
    setIsBusy(true);
    setNotice("");
    try {
      const analyzeResponse = await api<{ job: ParsedJob }>("/jobs/analyze", {
        title,
        company,
        description,
        url: url || null,
        location,
        source: "manual"
      });
      setJob(analyzeResponse.job);
      const scoreResponse = await api<{ score: FitScore }>("/jobs/score", { job: analyzeResponse.job });
      setFitScore(scoreResponse.score);
      setResume("");
      setResumePdfPath("");
      setCoverLetter("");
      setNotice("Job analyzed and scored.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to analyze job.");
    } finally {
      setIsBusy(false);
    }
  }

  async function discoverJobs() {
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<{ results: ScoredJobListing[]; source_errors: Record<string, string> }>("/jobs/search", {
        query: searchQuery,
        location,
        sources: sources.split(",").map((item) => item.trim()).filter(Boolean),
        manual_urls: manualUrls.split(/\s+/).map((item) => item.trim()).filter(Boolean),
        limit: 20
      });
      setSearchResults(response.results);
      setSourceErrors(response.source_errors);
      setNotice(`Found ${response.results.length} scored jobs.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to discover jobs.");
    } finally {
      setIsBusy(false);
    }
  }

  function selectSearchResult(result: ScoredJobListing) {
    setJob(result.parsed_job);
    setFitScore(result.score);
    setTitle(result.listing.title);
    setCompany(result.listing.company);
    setLocation(result.listing.location ?? "");
    setUrl(result.listing.url ?? "");
    setDescription(result.listing.description);
    setResume("");
    setResumePdfPath("");
    setCoverLetter("");
    setNotice("Search result loaded for review.");
  }

  async function generateMaterials() {
    if (!job) return;
    setIsBusy(true);
    setNotice("");
    try {
      const resumeResponse = await api<{ resume_markdown: string; resume_version: string; pdf_path?: string | null }>(
        "/resumes/generate",
        {
          job,
          fit_score: fitScore
        }
      );
      setResume(resumeResponse.resume_markdown);
      setResumeVersion(resumeResponse.resume_version);
      setResumePdfPath(resumeResponse.pdf_path ?? "");
      const letterResponse = await api<{ cover_letter: string }>("/cover-letter/generate", {
        job,
        resume_version: resumeResponse.resume_version
      });
      setCoverLetter(letterResponse.cover_letter);
      setNotice("Resume and cover letter generated for review.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to generate materials.");
    } finally {
      setIsBusy(false);
    }
  }

  async function saveApplication(status: "draft" | "approved" | "skipped") {
    if (!job) return;
    setIsBusy(true);
    setNotice("");
    try {
      const resolvedStatus = status === "draft" ? (resume ? "materials_generated" : "reviewed") : status;
      await api("/applications/save", {
        company: job.company,
        title: job.title,
        job_url: job.url,
        source: job.source,
        fit_score: fitScore?.score,
        recommendation: fitScore?.recommendation,
        resume_version: resumeVersion || null,
        resume_markdown: resume || null,
        resume_pdf_path: resumePdfPath || null,
        cover_letter: coverLetter || null,
        status: resolvedStatus,
        notes: resolvedStatus === "approved" ? "Approved by user for manual next step. Not submitted by system." : null
      });
      await refreshStats();
      await refreshApplications();
      setNotice(`Application saved as ${resolvedStatus}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to save application.");
    } finally {
      setIsBusy(false);
    }
  }

  async function createFillPlan() {
    if (!job?.url) {
      setNotice("A job URL is required for form filling.");
      return;
    }
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<{ fields: { label: string; value: string }[]; message: string }>("/forms/fill-plan", {
        application_url: job.url,
        resume_path: resumePdfPath || null,
        cover_letter: coverLetter || null,
        dry_run: true
      });
      setFillPlan(
        response.fields.map((field) =>
          `${field.label}: ${field.value.length > 80 ? `${field.value.slice(0, 80)}...` : field.value}`
        )
      );
      setNotice(response.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to create fill plan.");
    } finally {
      setIsBusy(false);
    }
  }

  async function updateApplicationStatus(applicationId: number) {
    const nextStatus = statusDrafts[applicationId];
    if (!nextStatus) return;
    setIsBusy(true);
    setNotice("");
    try {
      await api(`/applications/${applicationId}/status`, {
        status: nextStatus
      });
      await refreshStats();
      await refreshApplications();
      setNotice(`Application ${applicationId} updated to ${nextStatus}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to update application status.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Human-in-the-loop automation</p>
          <h1>Agentic Job Hunt Pipeline</h1>
        </div>
        <div className="stats" aria-label="Pipeline stats">
          <Metric label="Jobs" value={stats?.total_jobs ?? 0} />
          <Metric label="Avg fit" value={stats?.average_fit_score ?? "-"} />
          <Metric label="Approved" value={stats?.status_counts?.approved ?? 0} />
          <Metric label="Due follow-up" value={stats?.due_follow_ups ?? 0} />
        </div>
      </section>

      <section className="workspace">
        <form className="panel inputPanel" onSubmit={analyze}>
          <div className="panelHeader">
            <h2>Manual Job Input</h2>
            <button className="primaryButton" disabled={isBusy} type="submit">
              <WandSparkles size={18} aria-hidden />
              Analyze
            </button>
          </div>
          <label>
            Role
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </label>
          <label>
            Company
            <input value={company} onChange={(event) => setCompany(event.target.value)} required />
          </label>
          <label>
            Location
            <input value={location} onChange={(event) => setLocation(event.target.value)} />
          </label>
          <label>
            Job URL
            <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://..." />
          </label>
          <label className="descriptionField">
            Job Description
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} required />
          </label>
        </form>

        <section className="panel reviewPanel">
          <div className="panelHeader">
            <h2>Review Queue</h2>
            <span className={`pill ${recommendationTone}`}>{fitScore?.recommendation ?? "waiting"}</span>
          </div>

          {job ? (
            <div className="reviewStack">
              <div className="scoreRow">
                <div>
                  <p className="label">Fit score</p>
                  <strong className="score">{fitScore?.score ?? "-"}</strong>
                </div>
                <p>{fitScore?.rationale ?? "Score the job to see rationale."}</p>
              </div>

              <TagGroup title="Matched skills" items={fitScore?.matched_skills ?? []} />
              <TagGroup title="Missing skills" items={fitScore?.missing_skills ?? []} muted />
              <TagGroup title="Parsed requirements" items={job.required_skills} />

              <div className="actions">
                <button type="button" onClick={generateMaterials} disabled={isBusy}>
                  <FileText size={18} aria-hidden />
                  Generate
                </button>
                <button type="button" onClick={() => saveApplication("approved")} disabled={isBusy || !resume}>
                  <Check size={18} aria-hidden />
                  Approve
                </button>
                <button type="button" onClick={() => saveApplication("skipped")} disabled={isBusy}>
                  <SkipForward size={18} aria-hidden />
                  Skip
                </button>
                <button type="button" onClick={() => saveApplication("draft")} disabled={isBusy}>
                  <Save size={18} aria-hidden />
                  Save
                </button>
              </div>
            </div>
          ) : (
            <div className="emptyState">Paste a job description to begin the review flow.</div>
          )}
        </section>
      </section>

      <section className="panel discoveryPanel">
        <div className="panelHeader">
          <h2>Job Discovery</h2>
          <button type="button" onClick={discoverJobs} disabled={isBusy}>
            <Search size={18} aria-hidden />
            Search
          </button>
        </div>
        <div className="searchGrid">
          <label>
            Target
            <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
          </label>
          <label>
            Sources
            <input value={sources} onChange={(event) => setSources(event.target.value)} />
          </label>
          <label>
            Manual URLs
            <input
              value={manualUrls}
              onChange={(event) => setManualUrls(event.target.value)}
              placeholder="https://job-url.example"
            />
          </label>
        </div>
        {Object.entries(sourceErrors).length ? (
          <div className="sourceErrors">
            {Object.entries(sourceErrors).map(([source, error]) => (
              <span key={source}>{source}: {error}</span>
            ))}
          </div>
        ) : null}
        <div className="resultsGrid">
          {searchResults.map((result) => (
            <button
              className="resultCard"
              key={`${result.listing.source}-${result.listing.url}-${result.listing.title}`}
              type="button"
              onClick={() => selectSearchResult(result)}
            >
              <strong>{result.listing.title}</strong>
              <span>{result.listing.company} | {result.listing.location ?? "Location n/a"}</span>
              <span>{result.score.score}/100 | {result.score.recommendation}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel lifecyclePanel">
        <div className="panelHeader">
          <h2>Status Summary</h2>
        </div>
        <div className="tags">
          {APPLICATION_STATUSES.map((status) => (
            <span className="tag" key={status}>
              {status.replaceAll("_", " ")}: {stats?.status_counts?.[status] ?? 0}
            </span>
          ))}
        </div>
      </section>

      <section className="materials">
        <DocumentPanel title="Generated Resume" content={resume} />
        <DocumentPanel title="Generated Cover Letter" content={coverLetter} />
      </section>

      <section className="panel formPlan">
        <div className="panelHeader">
          <h2>Form Fill Review</h2>
          <button type="button" onClick={createFillPlan} disabled={isBusy || !job}>
            <Send size={18} aria-hidden />
            Plan Fill
          </button>
        </div>
        <div className="fillFields">
          {fillPlan.length ? (
            fillPlan.map((field) => <span key={field}>{field}</span>)
          ) : (
            <span className="muted">Create a fill plan after generating materials. Automation pauses before final submit.</span>
          )}
        </div>
      </section>

      <section className="panel history">
        <div className="panelHeader">
          <h2>Application Tracker</h2>
          <span>{applications.length} tracked</span>
        </div>
        <div className="table">
          {applications.map((application) => (
            <div className="tableRow" key={application.id}>
              <div>
                <strong>{application.title}</strong>
                <span>{application.company}</span>
              </div>
              <span>{application.fit_score ?? "-"} fit</span>
              <span>{application.recommendation ?? "n/a"}</span>
              <div className="statusControls">
                <select
                  value={statusDrafts[application.id] ?? application.status}
                  onChange={(event) =>
                    setStatusDrafts((current) => ({ ...current, [application.id]: event.target.value }))
                  }
                >
                  {APPLICATION_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
                <button type="button" onClick={() => updateApplicationStatus(application.id)} disabled={isBusy}>
                  Update
                </button>
              </div>
            </div>
          ))}
          {applications.length === 0 ? <div className="emptyState">No saved applications yet.</div> : null}
        </div>
      </section>

      {notice ? <div className="toast">{notice}</div> : null}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TagGroup({ title, items, muted = false }: { title: string; items: string[]; muted?: boolean }) {
  return (
    <div>
      <p className="label">{title}</p>
      <div className="tags">
        {items.length ? (
          items.map((item) => (
            <span className={muted ? "tag mutedTag" : "tag"} key={item}>
              {item}
            </span>
          ))
        ) : (
          <span className="muted">None parsed</span>
        )}
      </div>
    </div>
  );
}

function DocumentPanel({ title, content }: { title: string; content: string }) {
  return (
    <section className="panel documentPanel">
      <div className="panelHeader">
        <h2>{title}</h2>
      </div>
      <pre>{content || "Generated material will appear here after review."}</pre>
    </section>
  );
}
