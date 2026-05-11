from collections import Counter, defaultdict
import json
import re

from fastapi import Depends

from app.core.settings import Settings, get_settings
from app.db.sqlite import get_connection
from app.models.analytics import (
    AnalyticsOverviewResponse,
    CountItem,
    OutreachPerformanceResponse,
    RateMetric,
    RecommendationsResponse,
    ResumePerformanceItem,
    ResumePerformanceResponse,
    SkillGapItem,
    SkillGapsResponse,
    WeeklyInsightsResponse,
)


SUCCESS_STATUSES = {"interview", "offer"}
ACTIVE_STATUSES = {"reviewed", "materials_generated", "approved", "form_prepared", "applied", "submitted", "interview", "offer"}
REJECTION_STATUSES = {"rejected", "skipped"}


class AnalyticsService:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def overview(self) -> AnalyticsOverviewResponse:
        applications = self._rows("SELECT * FROM applications")
        resumes = self._rows("SELECT * FROM resume_versions")
        outreach = self._rows("SELECT * FROM outreach_records")
        total = len(applications)
        statuses = self._count_items(applications, "status")
        sources = self._count_items(applications, "source")
        roles = self._role_counts(applications)
        companies = self._count_items(applications, "company")
        ats_distribution = self._ats_distribution([row["fit_score"] for row in applications] + [row["ats_score"] for row in resumes])
        sent_or_replied = self._count_status(outreach, {"sent_manually", "replied", "no_response"})
        replies = self._count_status(outreach, {"replied"})

        return AnalyticsOverviewResponse(
            total_applications=total,
            applications_by_status=statuses,
            applications_by_source=sources,
            applications_by_role=roles,
            applications_by_ats_score_range=ats_distribution,
            applications_by_company=companies,
            response_rate=self._rate(self._count_status(applications, SUCCESS_STATUSES | {"submitted"}), total),
            interview_rate=self._rate(self._count_status(applications, {"interview", "offer"}), total),
            shortlisted_rate=self._rate(self._count_status(applications, ACTIVE_STATUSES), total),
            rejection_rate=self._rate(self._count_status(applications, REJECTION_STATUSES), total),
            outreach_reply_rate=self._rate(replies, sent_or_replied),
            average_ats_score=self._average([row["ats_score"] for row in resumes] + [row["fit_score"] for row in applications]),
            best_performing_resume_version=self._best_resume(resumes, applications),
            best_performing_job_source=self._best_source(applications),
            most_common_rejected_role_category=self._common_rejected_role(applications),
        )

    def skill_gaps(self) -> SkillGapsResponse:
        resumes = self._rows("SELECT * FROM resume_versions")
        counter: Counter[str] = Counter()
        for row in resumes:
            for skill in self._json_list(row["missing_keywords"]):
                normalized = self._normalize_label(skill)
                if normalized:
                    counter[normalized] += 1
        total_mentions = sum(counter.values())
        top = [
            SkillGapItem(skill=skill, count=count, percentage=self._percentage(count, max(1, len(resumes))))
            for skill, count in counter.most_common(10)
        ]
        return SkillGapsResponse(
            total_resume_versions=len(resumes),
            total_missing_keyword_mentions=total_mentions,
            top_missing_skills=top,
        )

    def resume_performance(self) -> ResumePerformanceResponse:
        resumes = self._rows("SELECT * FROM resume_versions ORDER BY created_at DESC")
        applications = self._rows("SELECT * FROM applications")
        items = [self._resume_item(row, applications) for row in resumes]
        selected = [item for item in items if item.status == "selected"]
        best = self._best_resume(resumes, applications)
        return ResumePerformanceResponse(
            versions=items,
            selected_resume_success=selected,
            best_performing_resume_version=best,
        )

    def outreach_performance(self) -> OutreachPerformanceResponse:
        records = self._rows("SELECT * FROM outreach_records")
        total = len(records)
        drafted = self._count_status(records, {"drafted"})
        sent = self._count_status(records, {"sent_manually"})
        replies = self._count_status(records, {"replied"})
        no_response = self._count_status(records, {"no_response"})
        sent_or_resolved = sent + replies + no_response
        followups = [row for row in records if str(row["message_type"]).startswith("follow_up")]
        followup_resolved = self._count_status(followups, {"sent_manually", "replied", "no_response"})
        by_channel = []
        for channel, group in self._group_by(records, "channel").items():
            resolved = self._count_status(group, {"sent_manually", "replied", "no_response"})
            by_channel.append(
                RateMetric(
                    label=channel,
                    numerator=self._count_status(group, {"replied"}),
                    denominator=resolved,
                    rate=self._rate(self._count_status(group, {"replied"}), resolved),
                )
            )
        return OutreachPerformanceResponse(
            total_records=total,
            drafted=drafted,
            sent_manually=sent,
            replies=replies,
            no_response=no_response,
            reply_rate=self._rate(replies, sent_or_resolved),
            follow_up_reply_rate=self._rate(self._count_status(followups, {"replied"}), followup_resolved),
            by_channel=sorted(by_channel, key=lambda item: item.label),
        )

    def weekly_insights(self) -> WeeklyInsightsResponse:
        applications = self._rows("SELECT * FROM applications")
        resumes = self._rows("SELECT * FROM resume_versions")
        outreach = self._rows("SELECT * FROM outreach_records")
        insights: list[str] = []
        sample_size = len(applications)
        if sample_size < 5:
            insights.append(f"Sample size is small ({sample_size} applications). Treat trends as directional until more local data is tracked.")
        source_scores = self._source_average_scores(applications)
        if len(source_scores) >= 2:
            best_source = max(source_scores.items(), key=lambda item: item[1])
            worst_source = min(source_scores.items(), key=lambda item: item[1])
            insights.append(f"{best_source[0]} has the highest average tracked ATS/fit score at {best_source[1]:.1f}, compared with {worst_source[0]} at {worst_source[1]:.1f}.")
        gaps = self.skill_gaps().top_missing_skills
        if gaps and self.skill_gaps().total_resume_versions:
            top_gap = gaps[0]
            insights.append(f"{top_gap.skill} appears in {top_gap.percentage:.0f}% of resume version gap reports.")
        outreach_perf = self.outreach_performance()
        if outreach_perf.reply_rate is not None:
            insights.append(f"Manual outreach reply rate is {outreach_perf.reply_rate:.1f}% across {outreach_perf.sent_manually + outreach_perf.replies + outreach_perf.no_response} resolved outreach records.")
        followup_replies = self._count_status([row for row in outreach if str(row["message_type"]).startswith("follow_up")], {"replied"})
        if followup_replies:
            insights.append(f"Follow-up messages have generated {followup_replies} replies in the local tracker.")
        best_resume = self._best_resume(resumes, applications)
        if best_resume:
            insights.append(f"{best_resume} is currently the strongest resume version by selected/success signals in local data.")
        return WeeklyInsightsResponse(sample_size=sample_size, insights=insights or ["No meaningful trends yet. Track more applications, resume versions, and outreach outcomes."])

    def recommendations(self) -> RecommendationsResponse:
        overview = self.overview()
        gaps = self.skill_gaps().top_missing_skills
        outreach = self.outreach_performance()
        return RecommendationsResponse(
            next_best_actions=self._next_actions(overview),
            resume_improvement_suggestions=[
                f"Review truthful evidence for {gap.skill}; it appears repeatedly in missing keyword reports."
                for gap in gaps[:3]
            ] or ["Generate more tailored resume versions before optimizing resume performance."],
            outreach_suggestions=self._outreach_suggestions(outreach),
            role_targeting_suggestions=self._role_suggestions(overview),
            follow_up_suggestions=["Review due and overdue follow-ups daily, then mark outcomes manually after sending outside the app."],
            skill_learning_priorities=[gap.skill for gap in gaps[:5]],
        )

    def _next_actions(self, overview: AnalyticsOverviewResponse) -> list[str]:
        actions = []
        if overview.total_applications < 5:
            actions.append("Track at least 5 applications before trusting performance trends.")
        if overview.average_ats_score is not None and overview.average_ats_score < 70:
            actions.append("Prioritize ATS tailoring before applying to more similar roles.")
        if overview.outreach_reply_rate is None:
            actions.append("Mark outreach outcomes manually so reply-rate analytics become useful.")
        actions.append("Check follow-ups due today and update statuses after manual outreach.")
        return actions

    def _outreach_suggestions(self, outreach: OutreachPerformanceResponse) -> list[str]:
        suggestions = []
        if outreach.total_records == 0:
            suggestions.append("Create outreach records after applying so channel performance can be measured.")
        elif outreach.reply_rate is not None and outreach.reply_rate < 10:
            suggestions.append("Shorten outreach drafts and personalize the strongest project or skill match.")
        else:
            suggestions.append("Keep sending outreach manually and mark replies/no-response to improve channel analytics.")
        return suggestions

    def _role_suggestions(self, overview: AnalyticsOverviewResponse) -> list[str]:
        rejected = overview.most_common_rejected_role_category
        if rejected:
            return [f"{rejected} is the most common rejected role category; compare ATS gaps before applying to more similar roles."]
        return ["Keep role categories consistent in titles so rejection and response patterns become clearer."]

    def _rows(self, sql: str) -> list[dict]:
        with get_connection(self.database_url) as connection:
            return [dict(row) for row in connection.execute(sql).fetchall()]

    def _count_items(self, rows: list[dict], key: str, limit: int = 10) -> list[CountItem]:
        counts = Counter(self._normalize_label(row.get(key) or "unknown") for row in rows)
        return [CountItem(label=label, count=count) for label, count in counts.most_common(limit)]

    def _role_counts(self, rows: list[dict]) -> list[CountItem]:
        counts = Counter(self._role_category(row.get("title") or "unknown") for row in rows)
        return [CountItem(label=label, count=count) for label, count in counts.most_common(10)]

    def _ats_distribution(self, scores: list[object]) -> list[CountItem]:
        buckets = {"0-39": 0, "40-59": 0, "60-79": 0, "80-100": 0, "unknown": 0}
        for score in scores:
            if score is None:
                buckets["unknown"] += 1
                continue
            value = int(score)
            if value < 40:
                buckets["0-39"] += 1
            elif value < 60:
                buckets["40-59"] += 1
            elif value < 80:
                buckets["60-79"] += 1
            else:
                buckets["80-100"] += 1
        return [CountItem(label=label, count=count) for label, count in buckets.items()]

    def _count_status(self, rows: list[dict], statuses: set[str]) -> int:
        return sum(1 for row in rows if row.get("status") in statuses)

    def _rate(self, numerator: int, denominator: int) -> float | None:
        if denominator <= 0:
            return None
        return round((numerator / denominator) * 100, 1)

    def _average(self, values: list[object]) -> float | None:
        numbers = [int(value) for value in values if value is not None]
        if not numbers:
            return None
        return round(sum(numbers) / len(numbers), 1)

    def _percentage(self, numerator: int, denominator: int) -> float:
        return round((numerator / denominator) * 100, 1) if denominator else 0

    def _group_by(self, rows: list[dict], key: str) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            grouped[self._normalize_label(row.get(key) or "unknown")].append(row)
        return grouped

    def _source_average_scores(self, applications: list[dict]) -> dict[str, float]:
        grouped = self._group_by([row for row in applications if row.get("fit_score") is not None], "source")
        return {source: self._average([row["fit_score"] for row in rows]) or 0 for source, rows in grouped.items() if len(rows) >= 1}

    def _best_source(self, applications: list[dict]) -> str | None:
        grouped = self._group_by(applications, "source")
        scored: list[tuple[str, int, int]] = []
        for source, rows in grouped.items():
            success = self._count_status(rows, SUCCESS_STATUSES | {"submitted"})
            scored.append((source, success, len(rows)))
        if not scored:
            return None
        source, success, total = max(scored, key=lambda item: (item[1], item[2]))
        return f"{source} ({success}/{total} positive outcomes)"

    def _best_resume(self, resumes: list[dict], applications: list[dict]) -> str | None:
        if not resumes:
            return None
        app_by_id = {row["id"]: row for row in applications}
        best = None
        best_score = -1
        for row in resumes:
            success = 0
            if row.get("application_id") in app_by_id and app_by_id[row["application_id"]].get("status") in SUCCESS_STATUSES:
                success += 2
            if row.get("status") == "selected":
                success += 1
            success += int(row.get("ats_score") or 0) / 100
            if success > best_score:
                best_score = success
                best = row
        return f"{best['resume_version_id']} ({best['title']})" if best else None

    def _resume_item(self, row: dict, applications: list[dict]) -> ResumePerformanceItem:
        app_by_id = {item["id"]: item for item in applications}
        success = 0
        if row.get("application_id") in app_by_id and app_by_id[row["application_id"]].get("status") in SUCCESS_STATUSES:
            success += 1
        return ResumePerformanceItem(
            resume_version_id=row["resume_version_id"],
            title=row["title"],
            company=row["company"],
            usage_count=1 if row.get("application_id") or row.get("job_queue_id") else 0,
            ats_score=row["ats_score"],
            status=row["status"],
            success_count=success,
        )

    def _common_rejected_role(self, applications: list[dict]) -> str | None:
        rejected = [row for row in applications if row.get("status") in REJECTION_STATUSES]
        if not rejected:
            return None
        return self._role_counts(rejected)[0].label

    def _role_category(self, title: str) -> str:
        value = title.lower()
        for token in ("product", "data", "frontend", "backend", "full-stack", "full stack", "ai", "ml", "machine learning"):
            if token in value:
                return "full stack" if token == "full-stack" else token
        return re.sub(r"\s+", " ", title.strip().lower()) or "unknown"

    def _normalize_label(self, value: object) -> str:
        return re.sub(r"\s+", " ", str(value).strip().lower()) or "unknown"

    def _json_list(self, value: object) -> list[str]:
        if not value:
            return []
        try:
            data = json.loads(str(value))
        except json.JSONDecodeError:
            return []
        return [str(item) for item in data if str(item).strip()]


def get_analytics_service(settings: Settings = Depends(get_settings)) -> AnalyticsService:
    return AnalyticsService(settings.database_url)
