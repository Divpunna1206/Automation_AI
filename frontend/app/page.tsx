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

type DailyTargetStats = {
  daily_target: number;
  applied_today: number;
  remaining_today: number;
  discovered_today: number;
  shortlisted_today: number;
  skipped_today: number;
};

type ApplicationListResponse = {
  applications: ApplicationRecord[];
};

type QueueJob = {
  id: number;
  title: string;
  company: string;
  job_url?: string | null;
  canonical_url?: string | null;
  source: string;
  location?: string | null;
  work_mode?: string | null;
  description: string;
  required_skills: string[];
  fit_score?: number | null;
  recommendation?: string | null;
  queue_status: string;
  discovered_at: string;
  updated_at: string;
};

type JobDiscoverResponse = {
  jobs: QueueJob[];
  inserted_count: number;
  duplicate_count: number;
  skipped_count: number;
  source_errors: Record<string, string>;
};

type QueueListResponse = {
  jobs: QueueJob[];
};

type ATSResult = {
  ats_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  required_skills_detected: string[];
  preferred_skills_detected: string[];
  matched_projects: string[];
  resume_gaps: string[];
  recommended_resume_angle: string;
  improvement_suggestions: string[];
  missing_keyword_action_plan: GapActionItem[];
  profile_update_suggestions: string[];
  safe_phrasing_suggestions: string[];
  warnings: string[];
  truthfulness_notes: string[];
  job: ParsedJob;
};

type GapActionItem = {
  skill: string;
  gap_type: string;
  priority: string;
  safe_resume_action: string;
  learning_action: string;
  interview_preparation_note: string;
};

type GapActionPlanResponse = {
  items: GapActionItem[];
  safe_phrasing_suggestions: string[];
  profile_update_suggestions: string[];
};

type ResumeVersion = {
  id: number;
  resume_version_id: string;
  job_queue_id?: number | null;
  application_id?: number | null;
  title: string;
  company: string;
  ats_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  file_path?: string | null;
  file_path_docx?: string | null;
  status: string;
  created_at: string;
};

type ResumeVersionListResponse = {
  versions: ResumeVersion[];
};

type FieldResult = {
  label: string;
  status: string;
  message: string;
  selector?: string | null;
  confidence: string;
};

type ApplySession = {
  id: number;
  job_queue_id?: number | null;
  application_id?: number | null;
  job_url: string;
  company: string;
  title: string;
  resume_version_id?: number | null;
  resume_file_path?: string | null;
  cover_letter_text?: string | null;
  status: string;
  fill_summary?: string | null;
  field_results: FieldResult[];
  screenshot_paths: string[];
  errors: string[];
  created_at: string;
  updated_at: string;
};

type ApplySessionListResponse = {
  sessions: ApplySession[];
};

type ApplySessionCreateResponse = {
  session: ApplySession;
  fill_plan: { label: string; value: string; kind: string }[];
  message: string;
};

type ApplyQuestion = {
  id: number;
  apply_session_id: number;
  question_text: string;
  detected_field_label?: string | null;
  answer_text?: string | null;
  confidence_score: number;
  answer_source: string;
  requires_manual_review: boolean;
  created_at: string;
  updated_at: string;
};

type ApplyQuestionListResponse = {
  questions: ApplyQuestion[];
};

type ReviewPack = {
  session: ApplySession;
  selected_resume_version?: number | null;
  resume_file_path?: string | null;
  cover_letter?: string | null;
  field_fill_summary?: string | null;
  unanswered_questions: ApplyQuestion[];
  generated_answers: ApplyQuestion[];
  warnings: string[];
  screenshots: string[];
  final_manual_checklist: string[];
};

type OutreachContact = {
  id: number;
  company: string;
  name?: string | null;
  title?: string | null;
  linkedin_url?: string | null;
  email?: string | null;
  source: string;
  confidence_score: number;
  notes?: string | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
};

type OutreachContactListResponse = {
  contacts: OutreachContact[];
};

type OutreachSuggestion = {
  search_queries: string[];
  company_domain?: string | null;
  guessed_email_patterns: { pattern: string; example: string; confidence_score: number; warning: string }[];
  warnings: string[];
};

type OutreachRecord = {
  id: number;
  job_queue_id?: number | null;
  application_id?: number | null;
  apply_session_id?: number | null;
  contact_id?: number | null;
  channel: string;
  message_type: string;
  message_text: string;
  status: string;
  follow_up_date?: string | null;
  created_at: string;
  updated_at: string;
};

type OutreachRecordListResponse = {
  records: OutreachRecord[];
};

type OutreachDashboard = {
  drafted: number;
  sent_manually: number;
  replies: number;
  no_response: number;
  follow_ups_due_today: number;
  overdue_follow_ups: number;
  upcoming_follow_ups: number;
};

type OutreachHistoryRecord = OutreachRecord & {
  company?: string | null;
  contact_name?: string | null;
  contact_title?: string | null;
};

type OutreachHistoryResponse = {
  records: OutreachHistoryRecord[];
};

type CountItem = {
  label: string;
  count: number;
};

type AnalyticsOverview = {
  total_applications: number;
  applications_by_status: CountItem[];
  applications_by_source: CountItem[];
  applications_by_role: CountItem[];
  applications_by_ats_score_range: CountItem[];
  applications_by_company: CountItem[];
  response_rate?: number | null;
  interview_rate?: number | null;
  shortlisted_rate?: number | null;
  rejection_rate?: number | null;
  outreach_reply_rate?: number | null;
  average_ats_score?: number | null;
  best_performing_resume_version?: string | null;
  best_performing_job_source?: string | null;
  most_common_rejected_role_category?: string | null;
};

type SkillGapAnalytics = {
  total_resume_versions: number;
  total_missing_keyword_mentions: number;
  top_missing_skills: { skill: string; count: number; percentage: number }[];
};

type ResumePerformanceAnalytics = {
  versions: {
    resume_version_id: string;
    title: string;
    company: string;
    usage_count: number;
    ats_score: number;
    status: string;
    success_count: number;
  }[];
  selected_resume_success: {
    resume_version_id: string;
    title: string;
    company: string;
    usage_count: number;
    ats_score: number;
    status: string;
    success_count: number;
  }[];
  best_performing_resume_version?: string | null;
};

type OutreachPerformanceAnalytics = {
  total_records: number;
  drafted: number;
  sent_manually: number;
  replies: number;
  no_response: number;
  reply_rate?: number | null;
  follow_up_reply_rate?: number | null;
  by_channel: { label: string; numerator: number; denominator: number; rate?: number | null }[];
};

type WeeklyInsights = {
  sample_size: number;
  insights: string[];
};

type AnalyticsRecommendations = {
  next_best_actions: string[];
  resume_improvement_suggestions: string[];
  outreach_suggestions: string[];
  role_targeting_suggestions: string[];
  follow_up_suggestions: string[];
  skill_learning_priorities: string[];
};

type SystemHealthCheck = {
  backend_status: string;
  database_reachable: boolean;
  config_valid: boolean;
  artifacts_writable: boolean;
  playwright_status: string;
  llm_status: string;
  frontend_api_base_url_suggestion: string;
  warnings: string[];
};

type DemoSeedResponse = {
  created_jobs: number;
  created_applications: number;
  created_resume_versions: number;
  created_contacts: number;
  created_outreach_records: number;
  message: string;
};

type ParsedUrlJob = {
  title: string;
  company: string;
  job_url: string;
  source: string;
  location?: string | null;
  description: string;
  message: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const APPLICATION_STATUSES = [
  "discovered",
  "reviewed",
  "materials_generated",
  "approved",
  "form_prepared",
  "applied",
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
  const [queueStatusFilter, setQueueStatusFilter] = useState("");
  const [queueSourceFilter, setQueueSourceFilter] = useState("");
  const [queueMinFitFilter, setQueueMinFitFilter] = useState("");
  const [queueLocationFilter, setQueueLocationFilter] = useState("");
  const [queueWorkModeFilter, setQueueWorkModeFilter] = useState("");
  const [queueSearchFilter, setQueueSearchFilter] = useState("");
  const [searchResults, setSearchResults] = useState<ScoredJobListing[]>([]);
  const [sourceErrors, setSourceErrors] = useState<Record<string, string>>({});
  const [queueJobs, setQueueJobs] = useState<QueueJob[]>([]);
  const [fillPlan, setFillPlan] = useState<string[]>([]);
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [statusDrafts, setStatusDrafts] = useState<Record<number, string>>({});
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [dailyTarget, setDailyTarget] = useState<DailyTargetStats | null>(null);
  const [atsResult, setAtsResult] = useState<ATSResult | null>(null);
  const [gapPlan, setGapPlan] = useState<GapActionPlanResponse | null>(null);
  const [resumeVersions, setResumeVersions] = useState<ResumeVersion[]>([]);
  const [applySessions, setApplySessions] = useState<ApplySession[]>([]);
  const [activeApplySession, setActiveApplySession] = useState<ApplySession | null>(null);
  const [applyQuestions, setApplyQuestions] = useState<ApplyQuestion[]>([]);
  const [reviewPack, setReviewPack] = useState<ReviewPack | null>(null);
  const [selectedResumeVersionId, setSelectedResumeVersionId] = useState("");
  const [outreachContacts, setOutreachContacts] = useState<OutreachContact[]>([]);
  const [outreachRecords, setOutreachRecords] = useState<OutreachRecord[]>([]);
  const [outreachDashboard, setOutreachDashboard] = useState<OutreachDashboard | null>(null);
  const [outreachFollowUps, setOutreachFollowUps] = useState<OutreachHistoryRecord[]>([]);
  const [outreachHistory, setOutreachHistory] = useState<OutreachHistoryRecord[]>([]);
  const [outreachSuggestions, setOutreachSuggestions] = useState<OutreachSuggestion | null>(null);
  const [analyticsOverview, setAnalyticsOverview] = useState<AnalyticsOverview | null>(null);
  const [skillGapAnalytics, setSkillGapAnalytics] = useState<SkillGapAnalytics | null>(null);
  const [resumePerformance, setResumePerformance] = useState<ResumePerformanceAnalytics | null>(null);
  const [outreachPerformance, setOutreachPerformance] = useState<OutreachPerformanceAnalytics | null>(null);
  const [weeklyInsights, setWeeklyInsights] = useState<WeeklyInsights | null>(null);
  const [analyticsRecommendations, setAnalyticsRecommendations] = useState<AnalyticsRecommendations | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealthCheck | null>(null);
  const [outreachCompany, setOutreachCompany] = useState("Acme AI");
  const [outreachRole, setOutreachRole] = useState("AI Engineer");
  const [outreachName, setOutreachName] = useState("");
  const [outreachTitle, setOutreachTitle] = useState("");
  const [outreachLinkedIn, setOutreachLinkedIn] = useState("");
  const [outreachEmail, setOutreachEmail] = useState("");
  const [outreachChannel, setOutreachChannel] = useState("linkedin");
  const [outreachMessage, setOutreachMessage] = useState("");
  const [selectedContactId, setSelectedContactId] = useState("");
  const [followUpView, setFollowUpView] = useState("due_today");
  const [copiedRecordId, setCopiedRecordId] = useState<number | null>(null);
  const [manualChecklist, setManualChecklist] = useState({
    reviewed: false,
    copied: false,
    sentOutside: false,
    statusUpdated: false
  });
  const [isBusy, setIsBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const recommendationTone = useMemo(() => {
    if (!fitScore) return "neutral";
    if (fitScore.recommendation === "approve") return "good";
    if (fitScore.recommendation === "skip") return "bad";
    return "warn";
  }, [fitScore]);

  async function api<T>(path: string, body?: unknown, method?: string): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        method: method ?? (body ? "POST" : "GET"),
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined
      });
    } catch {
      throw new Error(`Backend unavailable at ${API_BASE}. Start FastAPI on port 8000 or update NEXT_PUBLIC_API_BASE_URL.`);
    }
    if (!response.ok) {
      const error = await response.text();
      if (response.status === 404 && error.includes('"detail":"Not Found"')) {
        throw new Error(`Backend route ${path} was not found. Restart the FastAPI server so it loads the latest API routes.`);
      }
      throw new Error(readableError(error, `Request failed: ${response.status}`));
    }
    return response.json() as Promise<T>;
  }

  function readableError(raw: string, fallback: string) {
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") return parsed.detail;
      if (Array.isArray(parsed.detail)) return parsed.detail.map((item) => item.msg ?? JSON.stringify(item)).join("; ");
    } catch {
      // Keep the fallback path for non-JSON responses.
    }
    return raw && raw.length < 240 ? raw : fallback;
  }

  async function bootstrapDashboard() {
    try {
      await Promise.all([
        refreshStats(),
        refreshApplications(),
        refreshQueue(),
        refreshDailyTarget(),
        refreshResumeVersions(),
        refreshApplySessions(),
        refreshOutreachContacts(),
        refreshOutreachRecords(),
        refreshOutreachDashboard(),
        refreshFollowUps(),
        refreshOutreachHistory(),
        refreshAnalytics(),
        refreshSystemHealth()
      ]);
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

  async function refreshQueue() {
    const params = new URLSearchParams();
    if (queueStatusFilter) params.set("status", queueStatusFilter);
    if (queueSourceFilter) params.set("source", queueSourceFilter);
    if (queueMinFitFilter) params.set("min_fit_score", queueMinFitFilter);
    if (queueLocationFilter) params.set("location", queueLocationFilter);
    if (queueWorkModeFilter) params.set("work_mode", queueWorkModeFilter);
    if (queueSearchFilter) params.set("search", queueSearchFilter);
    const path = params.toString() ? `/jobs/queue?${params.toString()}` : "/jobs/queue";
    const response = await api<QueueListResponse>(path);
    setQueueJobs(response.jobs);
  }

  function clearQueueFilters() {
    setQueueStatusFilter("");
    setQueueSourceFilter("");
    setQueueMinFitFilter("");
    setQueueLocationFilter("");
    setQueueWorkModeFilter("");
    setQueueSearchFilter("");
    void api<QueueListResponse>("/jobs/queue").then((response) => setQueueJobs(response.jobs));
  }

  async function refreshDailyTarget() {
    const response = await api<DailyTargetStats>("/dashboard/daily-target");
    setDailyTarget(response);
  }

  async function refreshResumeVersions() {
    const response = await api<ResumeVersionListResponse>("/resumes/versions");
    setResumeVersions(response.versions);
  }

  async function refreshApplySessions() {
    const response = await api<ApplySessionListResponse>("/apply/sessions");
    setApplySessions(response.sessions);
    setActiveApplySession((current) => current ? response.sessions.find((session) => session.id === current.id) ?? current : response.sessions[0] ?? null);
  }

  async function refreshApplyQuestions(sessionId: number) {
    const response = await api<ApplyQuestionListResponse>(`/apply/sessions/${sessionId}/questions`);
    setApplyQuestions(response.questions);
  }

  async function refreshReviewPack(sessionId: number) {
    const response = await api<ReviewPack>(`/apply/sessions/${sessionId}/review-pack`);
    setReviewPack(response);
  }

  async function refreshOutreachContacts(companyFilter = outreachCompany) {
    const params = new URLSearchParams();
    if (companyFilter) params.set("company", companyFilter);
    const path = params.toString() ? `/outreach/contacts?${params.toString()}` : "/outreach/contacts";
    const response = await api<OutreachContactListResponse>(path);
    setOutreachContacts(response.contacts);
    setSelectedContactId((current) => current || (response.contacts[0] ? String(response.contacts[0].id) : ""));
  }

  async function refreshOutreachRecords() {
    const response = await api<OutreachRecordListResponse>("/outreach/records");
    setOutreachRecords(response.records);
  }

  async function refreshOutreachDashboard() {
    const response = await api<OutreachDashboard>("/outreach/dashboard");
    setOutreachDashboard(response);
  }

  async function refreshFollowUps(view = followUpView) {
    const params = new URLSearchParams();
    if (view === "due_today") params.set("due_today", "true");
    if (view === "overdue") params.set("overdue", "true");
    if (view === "upcoming") params.set("upcoming", "true");
    if (outreachCompany) params.set("company", outreachCompany);
    if (outreachChannel) params.set("channel", outreachChannel);
    const path = params.toString() ? `/outreach/follow-ups?${params.toString()}` : "/outreach/follow-ups";
    const response = await api<OutreachHistoryResponse>(path);
    setOutreachFollowUps(response.records);
  }

  async function refreshOutreachHistory() {
    const params = new URLSearchParams();
    if (selectedContactId) params.set("contact_id", selectedContactId);
    else if (outreachCompany) params.set("company", outreachCompany);
    const path = params.toString() ? `/outreach/history?${params.toString()}` : "/outreach/history";
    const response = await api<OutreachHistoryResponse>(path);
    setOutreachHistory(response.records);
  }

  async function refreshAnalytics() {
    const [overview, gaps, resumes, outreach, insights, recommendations] = await Promise.all([
      api<AnalyticsOverview>("/analytics/overview"),
      api<SkillGapAnalytics>("/analytics/skills-gaps"),
      api<ResumePerformanceAnalytics>("/analytics/resume-performance"),
      api<OutreachPerformanceAnalytics>("/analytics/outreach-performance"),
      api<WeeklyInsights>("/analytics/weekly-insights"),
      api<AnalyticsRecommendations>("/analytics/recommendations")
    ]);
    setAnalyticsOverview(overview);
    setSkillGapAnalytics(gaps);
    setResumePerformance(resumes);
    setOutreachPerformance(outreach);
    setWeeklyInsights(insights);
    setAnalyticsRecommendations(recommendations);
  }

  async function refreshSystemHealth() {
    const response = await api<SystemHealthCheck>("/system/health-check");
    setSystemHealth(response);
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
      const atsResponse = await api<ATSResult>("/ats/analyze", { job: analyzeResponse.job });
      setAtsResult(atsResponse);
      setGapPlan({
        items: atsResponse.missing_keyword_action_plan,
        safe_phrasing_suggestions: atsResponse.safe_phrasing_suggestions,
        profile_update_suggestions: atsResponse.profile_update_suggestions
      });
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
      const response = await api<JobDiscoverResponse>("/jobs/discover", {
        query: searchQuery,
        location,
        sources: sources.split(",").map((item) => item.trim()).filter(Boolean),
        manual_urls: manualUrls.split(/\s+/).map((item) => item.trim()).filter(Boolean),
        limit: 20
      });
      setSearchResults(
        response.jobs.map((queueJob) => ({
          listing: {
            title: queueJob.title,
            company: queueJob.company,
            description: queueJob.description,
            url: queueJob.job_url,
            location: queueJob.location,
            source: queueJob.source,
            tags: []
          },
          parsed_job: {
            title: queueJob.title,
            company: queueJob.company,
            description: queueJob.description,
            url: queueJob.job_url,
            location: queueJob.location,
            source: queueJob.source,
            required_skills: queueJob.required_skills,
            preferred_skills: [],
            responsibilities: [],
            risk_flags: []
          },
          score: {
            score: queueJob.fit_score ?? 0,
            recommendation: queueJob.recommendation ?? "review",
            matched_skills: [],
            missing_skills: [],
            concerns: [],
            rationale: "Saved to discovery queue.",
            signals: {}
          }
        }))
      );
      setSourceErrors(response.source_errors);
      await Promise.all([refreshQueue(), refreshDailyTarget()]);
      setNotice(
        `Discovery saved ${response.inserted_count} new jobs, found ${response.duplicate_count} duplicates, skipped ${response.skipped_count}.`
      );
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
      }, "PATCH");
      await refreshStats();
      await refreshApplications();
      setNotice(`Application ${applicationId} updated to ${nextStatus}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to update application status.");
    } finally {
      setIsBusy(false);
    }
  }

  async function generateTailoredResumeForCurrentJob() {
    if (!job) return;
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<{
        resume_markdown: string;
        resume_version: string;
        pdf_path?: string | null;
        ats: ATSResult;
      }>("/resumes/generate-tailored", { job });
      setResume(response.resume_markdown);
      setResumeVersion(response.resume_version);
      setResumePdfPath(response.pdf_path ?? "");
      setAtsResult(response.ats);
      setGapPlan({
        items: response.ats.missing_keyword_action_plan,
        safe_phrasing_suggestions: response.ats.safe_phrasing_suggestions,
        profile_update_suggestions: response.ats.profile_update_suggestions
      });
      await refreshResumeVersions();
      setNotice("Tailored resume generated with ATS analysis.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to generate tailored resume.");
    } finally {
      setIsBusy(false);
    }
  }

  async function parseUrlAndSaveToQueue() {
    const targetUrl = url || manualUrls.split(/\s+/).find(Boolean) || "";
    if (!targetUrl) {
      setNotice("Enter a job URL before parsing.");
      return;
    }
    setIsBusy(true);
    setNotice("");
    try {
      const parsed = await api<ParsedUrlJob>("/jobs/parse-url", { job_url: targetUrl });
      const analyzeResponse = await api<{ job: ParsedJob }>("/jobs/analyze", {
        title: parsed.title,
        company: parsed.company,
        description: parsed.description,
        url: parsed.job_url,
        location: parsed.location,
        source: parsed.source
      });
      const scoreResponse = await api<{ score: FitScore }>("/jobs/score", { job: analyzeResponse.job });
      await api<QueueJob>("/jobs/queue", {
        title: parsed.title,
        company: parsed.company,
        job_url: parsed.job_url,
        source: parsed.source,
        location: parsed.location,
        work_mode: parsed.location?.toLowerCase().includes("remote") ? "remote" : null,
        description: parsed.description,
        required_skills: analyzeResponse.job.required_skills,
        fit_score: scoreResponse.score.score,
        recommendation: scoreResponse.score.recommendation,
        queue_status: "discovered"
      });
      setTitle(parsed.title);
      setCompany(parsed.company);
      setLocation(parsed.location ?? "");
      setUrl(parsed.job_url);
      setDescription(parsed.description);
      setJob(analyzeResponse.job);
      setFitScore(scoreResponse.score);
      await Promise.all([refreshQueue(), refreshDailyTarget()]);
      setNotice(parsed.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to parse job URL.");
    } finally {
      setIsBusy(false);
    }
  }

  async function updateQueueJob(jobId: number, action: "shortlist" | "skip" | "convert") {
    setIsBusy(true);
    setNotice("");
    try {
      const path =
        action === "convert"
          ? `/jobs/queue/${jobId}/convert-to-application`
          : action === "shortlist"
            ? `/jobs/queue/${jobId}/shortlist`
            : `/jobs/queue/${jobId}/skip`;
      await api<QueueJob>(path, {});
      await Promise.all([refreshQueue(), refreshDailyTarget(), refreshApplications(), refreshStats()]);
      setNotice(
        action === "convert"
          ? "Job converted to application tracker. Human approval is still required before applying."
          : `Job ${action === "shortlist" ? "shortlisted" : "skipped"}.`
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to update queue job.");
    } finally {
      setIsBusy(false);
    }
  }

  async function analyzeQueueJob(jobId: number) {
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<ATSResult>("/ats/analyze", { job_queue_id: jobId });
      setAtsResult(response);
      setGapPlan({
        items: response.missing_keyword_action_plan,
        safe_phrasing_suggestions: response.safe_phrasing_suggestions,
        profile_update_suggestions: response.profile_update_suggestions
      });
      setJob(response.job);
      setTitle(response.job.title);
      setCompany(response.job.company);
      setLocation(response.job.location ?? "");
      setUrl(response.job.url ?? "");
      setDescription(response.job.description);
      setNotice(`ATS score: ${response.ats_score}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to analyze ATS.");
    } finally {
      setIsBusy(false);
    }
  }

  async function generateQueueResume(jobId: number) {
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<{
        resume_markdown: string;
        resume_version: string;
        pdf_path?: string | null;
        ats: ATSResult;
      }>("/resumes/generate-tailored", { job_queue_id: jobId });
      setResume(response.resume_markdown);
      setResumeVersion(response.resume_version);
      setResumePdfPath(response.pdf_path ?? "");
      setAtsResult(response.ats);
      setGapPlan({
        items: response.ats.missing_keyword_action_plan,
        safe_phrasing_suggestions: response.ats.safe_phrasing_suggestions,
        profile_update_suggestions: response.ats.profile_update_suggestions
      });
      setJob(response.ats.job);
      await refreshResumeVersions();
      setNotice("Tailored resume version created.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to generate queue resume.");
    } finally {
      setIsBusy(false);
    }
  }

  async function updateResumeVersion(versionId: number, action: "reviewed" | "selected" | "archived") {
    setIsBusy(true);
    setNotice("");
    try {
      if (action === "selected") {
        await api<ResumeVersion>(`/resumes/versions/${versionId}/select`, {});
      } else {
        await api<ResumeVersion>(
          `/resumes/versions/${versionId}/status`,
          { status: action === "reviewed" ? "reviewed" : "archived" },
          "PATCH"
        );
      }
      await refreshResumeVersions();
      setNotice(`Resume version marked ${action}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to update resume version.");
    } finally {
      setIsBusy(false);
    }
  }

  async function startApplySessionFromQueue(queueJob: QueueJob) {
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<ApplySessionCreateResponse>("/apply/sessions", {
        job_queue_id: queueJob.id,
        resume_version_id: selectedResumeVersionId ? Number(selectedResumeVersionId) : null,
        cover_letter_text: coverLetter || null
      });
      setActiveApplySession(response.session);
      await refreshApplySessions();
      await refreshApplyQuestions(response.session.id);
      setNotice(response.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to start apply session.");
    } finally {
      setIsBusy(false);
    }
  }

  async function runApplySession() {
    if (!activeApplySession) return;
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<ApplySession>(`/apply/sessions/${activeApplySession.id}/run-until-review`, {});
      setActiveApplySession(response);
      await refreshApplySessions();
      await refreshReviewPack(response.id);
      setNotice("Browser paused for manual review. This tool did not submit the application.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to run apply session.");
    } finally {
      setIsBusy(false);
    }
  }

  async function markApplySession(status: "completed-manually" | "failed") {
    if (!activeApplySession) return;
    setIsBusy(true);
    setNotice("");
    try {
      const path =
        status === "completed-manually"
          ? `/apply/sessions/${activeApplySession.id}/completed-manually`
          : `/apply/sessions/${activeApplySession.id}/failed`;
      const response = await api<ApplySession>(path, { message: status === "completed-manually" ? "Completed by user after manual review." : "Marked failed by user." }, "PATCH");
      setActiveApplySession(response);
      await refreshApplySessions();
      setNotice(`Apply session marked ${response.status}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to update apply session.");
    } finally {
      setIsBusy(false);
    }
  }

  async function generateApplyQuestions() {
    if (!activeApplySession) return;
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<ApplyQuestionListResponse>(`/apply/sessions/${activeApplySession.id}/questions/generate`, {});
      setApplyQuestions(response.questions);
      await refreshReviewPack(activeApplySession.id);
      setNotice("Application questions prepared for review.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to generate application questions.");
    } finally {
      setIsBusy(false);
    }
  }

  async function updateApplyQuestion(question: ApplyQuestion, answer: string) {
    const response = await api<ApplyQuestion>(
      `/apply/questions/${question.id}`,
      { answer_text: answer, requires_manual_review: false },
      "PATCH"
    );
    setApplyQuestions((current) => current.map((item) => (item.id === response.id ? response : item)));
  }

  async function markSubmittedManually() {
    if (!activeApplySession) return;
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<ApplySession>(`/apply/sessions/${activeApplySession.id}/mark-submitted-manually`, {}, "PATCH");
      setActiveApplySession(response);
      await Promise.all([refreshApplySessions(), refreshQueue(), refreshApplications(), refreshStats()]);
      setNotice("Marked submitted manually and updated linked local statuses.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to mark submitted manually.");
    } finally {
      setIsBusy(false);
    }
  }

  async function createOutreachContact() {
    setIsBusy(true);
    setNotice("");
    try {
      const contact = await api<OutreachContact>("/outreach/contacts", {
        company: outreachCompany,
        name: outreachName || null,
        title: outreachTitle || null,
        linkedin_url: outreachLinkedIn || null,
        email: outreachEmail || null,
        source: "manual",
        confidence_score: outreachEmail ? 0.6 : 0.7,
        notes: "Added manually in local outreach tracker."
      });
      setSelectedContactId(String(contact.id));
      setOutreachName("");
      setOutreachTitle("");
      setOutreachLinkedIn("");
      setOutreachEmail("");
      await Promise.all([refreshOutreachContacts(outreachCompany), refreshOutreachHistory()]);
      setNotice("Outreach contact saved locally.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to save outreach contact.");
    } finally {
      setIsBusy(false);
    }
  }

  async function archiveOutreachContact(contactId: number) {
    setIsBusy(true);
    setNotice("");
    try {
      await api<OutreachContact>(`/outreach/contacts/${contactId}`, { archived: true }, "PATCH");
      await Promise.all([refreshOutreachContacts(outreachCompany), refreshOutreachHistory()]);
      setNotice("Outreach contact archived.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to archive outreach contact.");
    } finally {
      setIsBusy(false);
    }
  }

  async function loadOutreachSuggestions() {
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<OutreachSuggestion>("/outreach/search-suggestions", {
        company: outreachCompany,
        role_title: outreachRole,
        job_url: url || null
      });
      setOutreachSuggestions(response);
      setNotice("Manual search suggestions prepared.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to prepare outreach suggestions.");
    } finally {
      setIsBusy(false);
    }
  }

  async function generateOutreachMessage() {
    setIsBusy(true);
    setNotice("");
    try {
      const contact = outreachContacts.find((item) => String(item.id) === selectedContactId);
      const response = await api<{ message_text: string; warnings: string[]; strongest_relevant_points: string[] }>(
        "/outreach/messages/generate",
        {
          company: outreachCompany,
          role_title: outreachRole,
          contact_name: (contact?.name ?? outreachName) || null,
          contact_title: (contact?.title ?? outreachTitle) || null,
          channel: outreachChannel,
          message_type: "initial"
        }
      );
      setOutreachMessage(response.message_text);
      setNotice(response.warnings.join(" "));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to generate outreach draft.");
    } finally {
      setIsBusy(false);
    }
  }

  async function saveOutreachRecord() {
    setIsBusy(true);
    setNotice("");
    try {
      await api<OutreachRecord>("/outreach/records", {
        contact_id: selectedContactId ? Number(selectedContactId) : null,
        channel: outreachChannel,
        message_type: "initial",
        message_text: outreachMessage,
        status: "drafted"
      });
      await Promise.all([refreshOutreachRecords(), refreshOutreachDashboard(), refreshFollowUps(), refreshOutreachHistory()]);
      setNotice("Outreach draft saved. Send manually outside this app when ready.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to save outreach record.");
    } finally {
      setIsBusy(false);
    }
  }

  async function updateOutreachRecordStatus(recordId: number, status: string) {
    setIsBusy(true);
    setNotice("");
    try {
      await api<OutreachRecord>(`/outreach/records/${recordId}/status`, { status }, "PATCH");
      await Promise.all([refreshOutreachRecords(), refreshOutreachDashboard(), refreshFollowUps(), refreshOutreachHistory(), refreshAnalytics()]);
      if (status === "sent_manually") {
        setManualChecklist((current) => ({ ...current, sentOutside: true, statusUpdated: true }));
      }
      setNotice(`Outreach record marked ${status.replaceAll("_", " ")}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to update outreach record.");
    } finally {
      setIsBusy(false);
    }
  }

  async function generateFollowUpMessage(record: OutreachHistoryRecord) {
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<{ message_text: string; warnings: string[]; strongest_relevant_points: string[] }>(
        "/outreach/messages/follow-up",
        {
          original_message: record.message_text,
          company: record.company ?? outreachCompany,
          role_title: outreachRole,
          days_since_first_message: 6,
          channel: record.channel,
          contact_name: record.contact_name ?? null
        }
      );
      setOutreachMessage(response.message_text);
      if (record.contact_id) setSelectedContactId(String(record.contact_id));
      setOutreachChannel(record.channel);
      setNotice(response.warnings.join(" "));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to generate follow-up draft.");
    } finally {
      setIsBusy(false);
    }
  }

  async function copyOutreachMessage(message: string, recordId?: number) {
    try {
      await navigator.clipboard.writeText(message);
      setCopiedRecordId(recordId ?? 0);
      setManualChecklist((current) => ({ ...current, copied: true }));
      setNotice("Message copied. Send it manually outside this app.");
    } catch {
      setNotice("Clipboard copy was blocked by the browser. Select the draft text and copy it manually.");
    }
  }

  async function seedDemoData() {
    setIsBusy(true);
    setNotice("");
    try {
      const response = await api<DemoSeedResponse>("/system/seed-demo-data", {});
      await Promise.all([
        refreshQueue(),
        refreshApplications(),
        refreshResumeVersions(),
        refreshOutreachContacts(outreachCompany),
        refreshOutreachRecords(),
        refreshAnalytics(),
        refreshSystemHealth()
      ]);
      setNotice(`${response.message} Jobs: ${response.created_jobs}, applications: ${response.created_applications}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to seed demo data.");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    void bootstrapDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dailyTargetValue = dailyTarget?.daily_target ?? 25;
  const appliedToday = dailyTarget?.applied_today ?? 0;
  const remainingToday = dailyTarget?.remaining_today ?? dailyTargetValue;
  const dailyProgress = Math.min(100, Math.round((appliedToday / Math.max(1, dailyTargetValue)) * 100));
  const targetMessage =
    remainingToday === 0
      ? "Target completed"
      : dailyProgress >= 50
        ? "On track"
        : `${remainingToday} applications remaining`;

  const contactCompanyGroups = useMemo(() => {
    const grouped = new Map<string, { company: string; contacts: OutreachContact[]; latestStatus: string; nextFollowUp: string | null }>();
    for (const contact of outreachContacts) {
      const current = grouped.get(contact.company) ?? {
        company: contact.company,
        contacts: [],
        latestStatus: "none",
        nextFollowUp: null
      };
      current.contacts.push(contact);
      grouped.set(contact.company, current);
    }
    for (const record of outreachHistory) {
      const companyName = record.company ?? "Unknown company";
      const current = grouped.get(companyName) ?? {
        company: companyName,
        contacts: [],
        latestStatus: "none",
        nextFollowUp: null
      };
      if (current.latestStatus === "none") current.latestStatus = record.status;
      if (record.follow_up_date && (!current.nextFollowUp || record.follow_up_date < current.nextFollowUp)) {
        current.nextFollowUp = record.follow_up_date;
      }
      grouped.set(companyName, current);
    }
    return Array.from(grouped.values()).sort((left, right) => left.company.localeCompare(right.company));
  }, [outreachContacts, outreachHistory]);

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
          <Metric label="Daily target" value={`${dailyTarget?.applied_today ?? 0}/${dailyTarget?.daily_target ?? 25}`} />
        </div>
      </section>

      <section className="panel lifecyclePanel">
        <div className="panelHeader">
          <h2>Daily Target</h2>
          <span>{targetMessage}</span>
        </div>
        <div className="progressTrack" aria-label="Daily target progress">
          <div className="progressFill" style={{ width: `${dailyProgress}%` }} />
        </div>
        <div className="tags">
          <span className="tag">Target: {dailyTargetValue}</span>
          <span className="tag">Applied: {appliedToday}</span>
          <span className="tag">Remaining: {remainingToday}</span>
          <span className="tag">Discovered: {dailyTarget?.discovered_today ?? 0}</span>
          <span className="tag">Shortlisted: {dailyTarget?.shortlisted_today ?? 0}</span>
          <span className="tag">Skipped: {dailyTarget?.skipped_today ?? 0}</span>
        </div>
      </section>

      <section className="panel lifecyclePanel">
        <div className="panelHeader">
          <h2>System Readiness</h2>
          <div className="actions">
            <button type="button" onClick={refreshSystemHealth} disabled={isBusy}>
              Check Setup
            </button>
            <button type="button" onClick={seedDemoData} disabled={isBusy}>
              Seed Demo Data
            </button>
          </div>
        </div>
        <div className="tags">
          <span className="tag">Backend: {systemHealth?.backend_status ?? "unknown"}</span>
          <span className="tag">DB: {systemHealth?.database_reachable ? "reachable" : "unknown"}</span>
          <span className="tag">Config: {systemHealth?.config_valid ? "valid" : "unknown"}</span>
          <span className="tag">Artifacts: {systemHealth?.artifacts_writable ? "writable" : "unknown"}</span>
          <span className="tag">Playwright: {systemHealth?.playwright_status ?? "unknown"}</span>
          <span className="tag">LLM: {systemHealth?.llm_status ?? "unknown"}</span>
        </div>
        <TagGroup title="Setup warnings" items={systemHealth?.warnings ?? []} muted />
      </section>

      <section className="panel history">
        <div className="panelHeader">
          <h2>Intelligence</h2>
          <button type="button" onClick={refreshAnalytics} disabled={isBusy}>
            Refresh
          </button>
        </div>
        <div className="stats intelligenceStats">
          <Metric label="Response rate" value={analyticsOverview?.response_rate != null ? `${analyticsOverview.response_rate}%` : "n/a"} />
          <Metric label="Interview rate" value={analyticsOverview?.interview_rate != null ? `${analyticsOverview.interview_rate}%` : "n/a"} />
          <Metric label="Avg ATS" value={analyticsOverview?.average_ats_score ?? "n/a"} />
          <Metric label="Outreach replies" value={outreachPerformance?.reply_rate != null ? `${outreachPerformance.reply_rate}%` : "n/a"} />
          <Metric label="Weekly sample" value={weeklyInsights?.sample_size ?? 0} />
          <Metric label="Follow-ups due" value={outreachDashboard?.follow_ups_due_today ?? 0} />
        </div>
        <div className="chartGrid">
          <BarChart title="Application funnel" items={analyticsOverview?.applications_by_status ?? []} />
          <BarChart title="ATS score distribution" items={analyticsOverview?.applications_by_ats_score_range ?? []} />
          <BarChart title="Job sources" items={analyticsOverview?.applications_by_source ?? []} />
          <BarChart title="Top missing skills" items={(skillGapAnalytics?.top_missing_skills ?? []).map((item) => ({ label: item.skill, count: item.count }))} />
          <BarChart title="Resume usage" items={(resumePerformance?.versions ?? []).slice(0, 8).map((item) => ({ label: item.resume_version_id, count: Math.max(1, item.usage_count) }))} />
          <BarChart title="Outreach channels" items={(outreachPerformance?.by_channel ?? []).map((item) => ({ label: item.label, count: item.numerator }))} />
        </div>
        <div className="analyticsGrid">
          <section>
            <p className="label">Weekly insights</p>
            <ul className="insightList">
              {(weeklyInsights?.insights ?? ["No weekly insights yet."]).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
          <section>
            <p className="label">Recommended next actions</p>
            <ul className="insightList">
              {(analyticsRecommendations?.next_best_actions ?? []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
          <section>
            <p className="label">Resume performance</p>
            <div className="tags">
              <span className="tag">Best: {resumePerformance?.best_performing_resume_version ?? "n/a"}</span>
              <span className="tag">Selected success: {resumePerformance?.selected_resume_success.length ?? 0}</span>
            </div>
          </section>
          <section>
            <p className="label">Targeting</p>
            <div className="tags">
              <span className="tag">Best source: {analyticsOverview?.best_performing_job_source ?? "n/a"}</span>
              <span className="tag">Rejected role: {analyticsOverview?.most_common_rejected_role_category ?? "n/a"}</span>
              <span className="tag">Most active source: {analyticsOverview?.applications_by_source[0]?.label ?? "n/a"}</span>
            </div>
          </section>
          <section>
            <p className="label">Skill priorities</p>
            <TagGroup title="Learning" items={analyticsRecommendations?.skill_learning_priorities ?? []} muted />
          </section>
          <section>
            <p className="label">Outreach suggestions</p>
            <TagGroup title="Suggestions" items={analyticsRecommendations?.outreach_suggestions ?? []} muted />
          </section>
        </div>
      </section>

      <section className="workspace">
        <form className="panel inputPanel" onSubmit={analyze}>
          <div className="panelHeader">
            <h2>Manual Job Input</h2>
            <div className="actions">
              <button type="button" onClick={parseUrlAndSaveToQueue} disabled={isBusy || !url}>
                <Search size={18} aria-hidden />
                Parse URL
              </button>
              <button className="primaryButton" disabled={isBusy} type="submit">
                <WandSparkles size={18} aria-hidden />
                Analyze
              </button>
            </div>
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
                <button type="button" onClick={generateTailoredResumeForCurrentJob} disabled={isBusy}>
                  <FileText size={18} aria-hidden />
                  ATS Resume
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
            <select value={sources} onChange={(event) => setSources(event.target.value)}>
              <option value="manual">manual</option>
              <option value="remoteok">remoteok</option>
              <option value="remoteok,manual">remoteok, manual</option>
            </select>
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

      <section className="panel lifecyclePanel">
        <div className="panelHeader">
          <h2>ATS Analysis</h2>
          <span>{atsResult ? `${atsResult.ats_score}/100` : "waiting"}</span>
        </div>
        {atsResult ? (
          <div className="reviewStack">
            <p>{atsResult.recommended_resume_angle}</p>
            <TagGroup title="Matched keywords" items={atsResult.matched_keywords} />
            <TagGroup title="Missing keywords" items={atsResult.missing_keywords} muted />
            <TagGroup title="Required skills" items={atsResult.required_skills_detected} />
            <TagGroup title="Preferred skills" items={atsResult.preferred_skills_detected} muted />
            <TagGroup title="Matched projects" items={atsResult.matched_projects} />
            <TagGroup title="Improvements" items={atsResult.improvement_suggestions} />
            <TagGroup title="Warnings" items={atsResult.warnings} muted />
          </div>
        ) : (
          <div className="emptyState">Analyze a job or queue item to see ATS guidance.</div>
        )}
      </section>

      <section className="panel lifecyclePanel">
        <div className="panelHeader">
          <h2>Gap Action Plan</h2>
          <span>{gapPlan?.items.length ?? 0} gaps</span>
        </div>
        {gapPlan?.items.length ? (
          <div className="table">
            {gapPlan.items.map((item) => (
              <div className="tableRow" key={item.skill}>
                <div>
                  <strong>{item.skill}</strong>
                  <span>{item.safe_resume_action}</span>
                </div>
                <span>{item.gap_type}</span>
                <span>{item.priority}</span>
                <span>{item.learning_action}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="emptyState">No gap action plan yet.</div>
        )}
        <TagGroup title="Safe phrasing" items={gapPlan?.safe_phrasing_suggestions ?? []} muted />
      </section>

      <section className="panel history">
        <div className="panelHeader">
          <h2>Discovery Queue</h2>
          <span>{queueJobs.length} saved</span>
        </div>
        <div className="filterGrid">
          <label>
            Status
            <select value={queueStatusFilter} onChange={(event) => setQueueStatusFilter(event.target.value)}>
              <option value="">Any</option>
              <option value="discovered">Discovered</option>
              <option value="shortlisted">Shortlisted</option>
              <option value="skipped">Skipped</option>
              <option value="applied">Applied</option>
            </select>
          </label>
          <label>
            Source
            <select value={queueSourceFilter} onChange={(event) => setQueueSourceFilter(event.target.value)}>
              <option value="">Any</option>
              <option value="manual">Manual</option>
              <option value="remoteok">RemoteOK</option>
            </select>
          </label>
          <label>
            Min fit
            <input
              min="0"
              max="100"
              type="number"
              value={queueMinFitFilter}
              onChange={(event) => setQueueMinFitFilter(event.target.value)}
            />
          </label>
          <label>
            Location
            <input value={queueLocationFilter} onChange={(event) => setQueueLocationFilter(event.target.value)} />
          </label>
          <label>
            Work mode
            <select value={queueWorkModeFilter} onChange={(event) => setQueueWorkModeFilter(event.target.value)}>
              <option value="">Any</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">Onsite</option>
            </select>
          </label>
          <label>
            Search
            <input value={queueSearchFilter} onChange={(event) => setQueueSearchFilter(event.target.value)} />
          </label>
          <div className="filterActions">
            <button type="button" onClick={refreshQueue} disabled={isBusy}>Apply</button>
            <button type="button" onClick={clearQueueFilters} disabled={isBusy}>Clear</button>
          </div>
        </div>
        <div className="table">
          {queueJobs.map((queueJob) => (
            <div className="tableRow queueRow" key={queueJob.id}>
              <div>
                <strong>{queueJob.title}</strong>
                <span>{queueJob.company} | {queueJob.source} | {queueJob.location ?? "Location n/a"}</span>
              </div>
              <span>{queueJob.fit_score ?? "-"} fit</span>
              <span>{queueJob.recommendation ?? "review"}</span>
              <span className="tag">{queueJob.queue_status.replaceAll("_", " ")}</span>
              <div className="statusControls">
                <button
                  type="button"
                  onClick={() => analyzeQueueJob(queueJob.id)}
                  disabled={isBusy}
                >
                  ATS
                </button>
                <button
                  type="button"
                  onClick={() => generateQueueResume(queueJob.id)}
                  disabled={isBusy}
                >
                  Resume
                </button>
                <button
                  type="button"
                  onClick={() => updateQueueJob(queueJob.id, "shortlist")}
                  disabled={isBusy || queueJob.queue_status === "shortlisted" || queueJob.queue_status === "applied"}
                >
                  Shortlist
                </button>
                <button
                  type="button"
                  onClick={() => updateQueueJob(queueJob.id, "skip")}
                  disabled={isBusy || queueJob.queue_status === "skipped" || queueJob.queue_status === "applied"}
                >
                  Skip
                </button>
                <button
                  type="button"
                  onClick={() => updateQueueJob(queueJob.id, "convert")}
                  disabled={isBusy || queueJob.queue_status === "applied"}
                >
                  Convert
                </button>
                <button
                  type="button"
                  onClick={() => startApplySessionFromQueue(queueJob)}
                  disabled={isBusy || !queueJob.job_url}
                >
                  Apply Assist
                </button>
              </div>
            </div>
          ))}
          {queueJobs.length === 0 ? <div className="emptyState">No discovered jobs saved yet.</div> : null}
        </div>
      </section>

      <section className="materials">
        <DocumentPanel title="Generated Resume" content={resume} />
        <DocumentPanel title="Generated Cover Letter" content={coverLetter} />
      </section>

      <section className="panel history">
        <div className="panelHeader">
          <h2>Resume Versions</h2>
          <span>{resumeVersions.length} versions</span>
        </div>
        <label>
          Resume for apply assistant
          <select value={selectedResumeVersionId} onChange={(event) => setSelectedResumeVersionId(event.target.value)}>
            <option value="">Use selected/latest</option>
            {resumeVersions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.title} | {version.company} | {version.status}
              </option>
            ))}
          </select>
        </label>
        <div className="table">
          {resumeVersions.map((version) => (
            <div className="tableRow" key={version.id}>
              <div>
                <strong>{version.title}</strong>
                <span>{version.company} | {version.resume_version_id}</span>
              </div>
              <span>{version.ats_score} ATS</span>
              <span className="tag">{version.status}</span>
              <div className="statusControls">
                <button type="button" onClick={() => updateResumeVersion(version.id, "reviewed")} disabled={isBusy}>
                  Reviewed
                </button>
                <button type="button" onClick={() => updateResumeVersion(version.id, "selected")} disabled={isBusy}>
                  Select
                </button>
                <button type="button" onClick={() => updateResumeVersion(version.id, "archived")} disabled={isBusy}>
                  Archive
                </button>
              </div>
              <div>
                <span>{version.file_path ?? "PDF n/a"}</span>
                <span>{version.file_path_docx ?? "DOCX n/a"}</span>
              </div>
            </div>
          ))}
          {resumeVersions.length === 0 ? <div className="emptyState">No tailored resume versions yet.</div> : null}
        </div>
      </section>

      <section className="panel history">
        <div className="panelHeader">
          <h2>Outreach</h2>
          <span>{outreachRecords.length} records</span>
        </div>
        <p className="muted">Manual CRM only. This app does not scrape contacts or send messages.</p>
        <div className="tags">
          <span className="tag">Drafted: {outreachDashboard?.drafted ?? 0}</span>
          <span className="tag">Sent manually: {outreachDashboard?.sent_manually ?? 0}</span>
          <span className="tag">Replies: {outreachDashboard?.replies ?? 0}</span>
          <span className="tag">No response: {outreachDashboard?.no_response ?? 0}</span>
          <span className="tag">Due today: {outreachDashboard?.follow_ups_due_today ?? 0}</span>
          <span className="tag">Overdue: {outreachDashboard?.overdue_follow_ups ?? 0}</span>
          <span className="tag">Upcoming: {outreachDashboard?.upcoming_follow_ups ?? 0}</span>
        </div>
        <div className="searchGrid">
          <label>
            Company
            <input value={outreachCompany} onChange={(event) => setOutreachCompany(event.target.value)} />
          </label>
          <label>
            Role
            <input value={outreachRole} onChange={(event) => setOutreachRole(event.target.value)} />
          </label>
          <label>
            Channel
            <select value={outreachChannel} onChange={(event) => setOutreachChannel(event.target.value)}>
              <option value="linkedin">LinkedIn</option>
              <option value="email">Email</option>
              <option value="other">Other</option>
            </select>
          </label>
          <div className="filterActions">
            <button type="button" onClick={() => refreshOutreachContacts(outreachCompany)} disabled={isBusy}>
              Load Contacts
            </button>
            <button type="button" onClick={refreshOutreachHistory} disabled={isBusy}>
              History
            </button>
            <button type="button" onClick={loadOutreachSuggestions} disabled={isBusy || !outreachCompany}>
              Search Ideas
            </button>
          </div>
        </div>
        <div className="searchGrid">
          <label>
            Name
            <input value={outreachName} onChange={(event) => setOutreachName(event.target.value)} />
          </label>
          <label>
            Title
            <input value={outreachTitle} onChange={(event) => setOutreachTitle(event.target.value)} />
          </label>
          <label>
            LinkedIn URL
            <input value={outreachLinkedIn} onChange={(event) => setOutreachLinkedIn(event.target.value)} />
          </label>
          <label>
            Email
            <input value={outreachEmail} onChange={(event) => setOutreachEmail(event.target.value)} />
          </label>
          <div className="filterActions">
            <button type="button" onClick={createOutreachContact} disabled={isBusy || !outreachCompany}>
              Add Contact
            </button>
          </div>
        </div>
        {outreachSuggestions ? (
          <div className="reviewStack">
            <TagGroup title="Manual searches" items={outreachSuggestions.search_queries} />
            <TagGroup title="Warnings" items={outreachSuggestions.warnings} muted />
            <div className="table">
              {outreachSuggestions.guessed_email_patterns.map((guess) => (
                <div className="tableRow" key={guess.example}>
                  <div>
                    <strong>{guess.example}</strong>
                    <span>{guess.warning}</span>
                  </div>
                  <span>{Math.round(guess.confidence_score * 100)}%</span>
                  <span>low confidence</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        <div className="table">
          {contactCompanyGroups.map((group) => (
            <div className="tableRow" key={group.company}>
              <div>
                <strong>{group.company}</strong>
                <span>{group.contacts.length} contacts saved</span>
              </div>
              <span>{group.latestStatus.replaceAll("_", " ")}</span>
              <span>{group.nextFollowUp ?? "no follow-up"}</span>
              <button
                type="button"
                onClick={() => {
                  setOutreachCompany(group.company);
                  void refreshOutreachContacts(group.company);
                }}
                disabled={isBusy}
              >
                Open
              </button>
            </div>
          ))}
        </div>
        <div className="table">
          {outreachContacts.map((contact) => (
            <div className="tableRow" key={contact.id}>
              <div>
                <strong>{contact.name || "Unknown contact"}</strong>
                <span>{contact.title ?? "Title n/a"} | {contact.company}</span>
              </div>
              <span>{contact.email ?? "email n/a"}</span>
              <span>{contact.linkedin_url ?? "linkedin n/a"}</span>
              <div className="statusControls">
                <button type="button" onClick={() => setSelectedContactId(String(contact.id))} disabled={isBusy}>
                  Select
                </button>
                <button type="button" onClick={() => archiveOutreachContact(contact.id)} disabled={isBusy}>
                  Archive
                </button>
              </div>
            </div>
          ))}
          {outreachContacts.length === 0 ? <div className="emptyState">No contacts saved for this company.</div> : null}
        </div>
        <div className="reviewStack">
          <label>
            Contact for draft
            <select value={selectedContactId} onChange={(event) => setSelectedContactId(event.target.value)}>
              <option value="">No contact selected</option>
              {outreachContacts.map((contact) => (
                <option key={contact.id} value={contact.id}>
                  {contact.name || contact.email || contact.linkedin_url || `Contact ${contact.id}`}
                </option>
              ))}
            </select>
          </label>
          <div className="actions">
            <button type="button" onClick={generateOutreachMessage} disabled={isBusy || !outreachCompany || !outreachRole}>
              Generate Draft
            </button>
            <button type="button" onClick={() => copyOutreachMessage(outreachMessage)} disabled={isBusy || !outreachMessage}>
              {copiedRecordId === 0 ? "Copied" : "Copy Message"}
            </button>
            <button type="button" onClick={saveOutreachRecord} disabled={isBusy || !outreachMessage}>
              Save Draft
            </button>
          </div>
          <textarea value={outreachMessage} onChange={(event) => setOutreachMessage(event.target.value)} />
          <div className="checklist">
            <label>
              <input
                type="checkbox"
                checked={manualChecklist.reviewed}
                onChange={(event) => setManualChecklist((current) => ({ ...current, reviewed: event.target.checked }))}
              />
              Message reviewed
            </label>
            <label>
              <input
                type="checkbox"
                checked={manualChecklist.copied}
                onChange={(event) => setManualChecklist((current) => ({ ...current, copied: event.target.checked }))}
              />
              Copied manually
            </label>
            <label>
              <input
                type="checkbox"
                checked={manualChecklist.sentOutside}
                onChange={(event) => setManualChecklist((current) => ({ ...current, sentOutside: event.target.checked }))}
              />
              Sent manually outside app
            </label>
            <label>
              <input
                type="checkbox"
                checked={manualChecklist.statusUpdated}
                onChange={(event) => setManualChecklist((current) => ({ ...current, statusUpdated: event.target.checked }))}
              />
              Status updated
            </label>
          </div>
        </div>
        <div className="table">
          {outreachRecords.map((record) => (
            <div className="tableRow" key={record.id}>
              <div>
                <strong>{record.channel} | {record.message_type.replaceAll("_", " ")}</strong>
                <span>{record.message_text}</span>
              </div>
              <span className="tag">{record.status.replaceAll("_", " ")}</span>
              <span>{record.follow_up_date ?? "follow-up n/a"}</span>
              <div className="statusControls">
                <button type="button" onClick={() => copyOutreachMessage(record.message_text, record.id)} disabled={isBusy}>
                  {copiedRecordId === record.id ? "Copied" : "Copy"}
                </button>
                <button type="button" onClick={() => updateOutreachRecordStatus(record.id, "sent_manually")} disabled={isBusy}>
                  Sent Manually
                </button>
                <button type="button" onClick={() => updateOutreachRecordStatus(record.id, "replied")} disabled={isBusy}>
                  Replied
                </button>
                <button type="button" onClick={() => updateOutreachRecordStatus(record.id, "no_response")} disabled={isBusy}>
                  No Response
                </button>
              </div>
            </div>
          ))}
          {outreachRecords.length === 0 ? <div className="emptyState">No outreach records yet.</div> : null}
        </div>
        <div className="reviewStack">
          <div className="panelHeader">
            <h2>Follow-ups</h2>
            <span>{outreachFollowUps.length} visible</span>
          </div>
          <div className="actions">
            {["due_today", "overdue", "upcoming"].map((view) => (
              <button
                type="button"
                key={view}
                onClick={() => {
                  setFollowUpView(view);
                  void refreshFollowUps(view);
                }}
                disabled={isBusy}
              >
                {view.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <div className="table">
            {outreachFollowUps.map((record) => (
              <div className="tableRow" key={`follow-up-${record.id}`}>
                <div>
                  <strong>{record.company ?? "Company n/a"}</strong>
                  <span>{record.contact_name ?? "Contact n/a"} | {record.channel}</span>
                </div>
                <span>{record.follow_up_date ?? "n/a"}</span>
                <span>{record.status.replaceAll("_", " ")}</span>
                <div className="statusControls">
                  <button type="button" onClick={() => generateFollowUpMessage(record)} disabled={isBusy}>
                    Draft Follow-up
                  </button>
                  <button type="button" onClick={() => updateOutreachRecordStatus(record.id, "no_response")} disabled={isBusy}>
                    No Response
                  </button>
                </div>
              </div>
            ))}
            {outreachFollowUps.length === 0 ? <div className="emptyState">No follow-ups match this view.</div> : null}
          </div>
        </div>
        <div className="reviewStack">
          <div className="panelHeader">
            <h2>Message History</h2>
            <span>{outreachHistory.length} messages</span>
          </div>
          <div className="table">
            {outreachHistory.map((record) => (
              <div className="tableRow" key={`history-${record.id}`}>
                <div>
                  <strong>{record.message_type.replaceAll("_", " ")} | {record.company ?? "Company n/a"}</strong>
                  <span>{record.message_text}</span>
                </div>
                <span>{record.channel}</span>
                <span>{record.status.replaceAll("_", " ")}</span>
                <span>{record.follow_up_date ?? "no follow-up"}</span>
              </div>
            ))}
            {outreachHistory.length === 0 ? <div className="emptyState">No message history for this filter.</div> : null}
          </div>
        </div>
      </section>

      <section className="panel history">
        <div className="panelHeader">
          <h2>Apply Assistant</h2>
          <span>{activeApplySession?.status ?? `${applySessions.length} sessions`}</span>
        </div>
        <p className="muted">This tool fills fields for review only. It does not submit applications.</p>
        {activeApplySession ? (
          <div className="reviewStack">
            <div className="scoreRow">
              <div>
                <p className="label">Session</p>
                <strong>{activeApplySession.id}</strong>
              </div>
              <p>{activeApplySession.title} at {activeApplySession.company}</p>
            </div>
            <div className="actions">
              <button type="button" onClick={runApplySession} disabled={isBusy || activeApplySession.status === "review_required"}>
                Run Until Review
              </button>
              <button type="button" onClick={() => markApplySession("completed-manually")} disabled={isBusy}>
                Mark Completed Manually
              </button>
              <button type="button" onClick={() => markApplySession("failed")} disabled={isBusy}>
                Mark Failed
              </button>
              <button type="button" onClick={generateApplyQuestions} disabled={isBusy}>
                Generate Questions
              </button>
              <button type="button" onClick={() => refreshReviewPack(activeApplySession.id)} disabled={isBusy}>
                Review Pack
              </button>
              <button type="button" onClick={markSubmittedManually} disabled={isBusy}>
                Mark Submitted Manually
              </button>
            </div>
            <section>
              <p className="label">Questions</p>
              <div className="table">
                {applyQuestions.map((question) => (
                  <div className="tableRow" key={question.id}>
                    <div>
                      <strong>{question.detected_field_label ?? "Question"}</strong>
                      <span>{question.question_text}</span>
                      <input
                        defaultValue={question.answer_text ?? ""}
                        onBlur={(event) => updateApplyQuestion(question, event.target.value)}
                      />
                    </div>
                    <span>{Math.round(question.confidence_score * 100)}%</span>
                    <span>{question.answer_source}</span>
                    <span>{question.requires_manual_review ? "manual review" : "ready"}</span>
                  </div>
                ))}
                {applyQuestions.length === 0 ? <div className="emptyState">Generate questions for this session.</div> : null}
              </div>
            </section>
            {reviewPack ? (
              <section>
                <p className="label">Review Pack</p>
                <TagGroup title="Warnings" items={reviewPack.warnings} muted />
                <TagGroup title="Screenshots" items={reviewPack.screenshots} muted />
                <TagGroup title="Checklist" items={reviewPack.final_manual_checklist} />
                <TagGroup title="Manual required" items={reviewPack.unanswered_questions.map((question) => question.question_text)} muted />
              </section>
            ) : null}
            <TagGroup title="Screenshots" items={activeApplySession.screenshot_paths} muted />
            <TagGroup title="Errors" items={activeApplySession.errors} muted />
            <div className="table">
              {activeApplySession.field_results.map((field) => (
                <div className="tableRow" key={`${field.label}-${field.selector ?? field.status}`}>
                  <div>
                    <strong>{field.label}</strong>
                    <span>{field.message}</span>
                  </div>
                  <span>{field.status}</span>
                  <span>{field.confidence}</span>
                  <span>{field.selector ?? "manual"}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="emptyState">Start from a queue job with Apply Assist.</div>
        )}
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

function BarChart({ title, items }: { title: string; items: CountItem[] }) {
  const max = Math.max(1, ...items.map((item) => item.count));
  return (
    <section className="chartPanel">
      <p className="label">{title}</p>
      <div className="barList">
        {items.length ? (
          items.map((item) => (
            <div className="barRow" key={`${title}-${item.label}`}>
              <span>{item.label}</span>
              <div className="barTrack">
                <div className="barFill" style={{ width: `${Math.max(4, (item.count / max) * 100)}%` }} />
              </div>
              <strong>{item.count}</strong>
            </div>
          ))
        ) : (
          <span className="muted">No tracked data yet.</span>
        )}
      </div>
    </section>
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
