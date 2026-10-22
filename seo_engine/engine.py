"""
Master SEO Engine for J.A.R.V.I.S.

Orchestrates:
1. URL Fetcher & SSRF Validator / Local Project Reader
2. Deterministic SEO Analyzer
3. Explainable Category & Composite Scorer
4. Issue Prioritizer & Action Plan Generator
5. Evidence-Grounded AI Recommendation Interpreter
6. Markdown / JSON Export Generator
"""

import time
from typing import Dict, Any, Optional, Callable

from seo_engine.models import (
    SEOAuditReport,
    ScoreTier
)
from seo_engine.fetcher import SEOFetcher, FetchResult
from seo_engine.analyzer import SEOAnalyzer
from seo_engine.scoring import SEOScoringEngine
from seo_engine.prioritizer import SEOPrioritizer
from seo_engine.ai_interpreter import SEOAIInterpreter


class SEOEngine:
    """
    Unified entrypoint for URL and local project SEO Intelligence audits.
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        self.log_callback = log_callback

    def _log(self, stage: str, message: str):
        formatted = f"[SEO_{stage.upper()}] {message}"
        print(formatted)
        if self.log_callback:
            try:
                self.log_callback(stage, message)
            except Exception:
                pass

    def analyze_url(
        self,
        url: str,
        target_keyword: Optional[str] = None,
        use_llm: bool = True
    ) -> SEOAuditReport:
        """
        Runs an end-to-end SEO Intelligence audit for a public URL.
        """
        start_time = time.time()
        self._log("CONNECT", f"Initiating secure connection to '{url}'...")

        # 1. Fetch document safely
        fetch_res = SEOFetcher.fetch_url(url)
        if not fetch_res.success:
            self._log("ERROR", f"Failed to retrieve URL: {fetch_res.error}")
            report = SEOAuditReport(
                target=url,
                mode="url",
                target_keyword=target_keyword,
                overall_score=0.0,
                tier=ScoreTier.NEEDS_IMPROVEMENT,
                summary=f"Audit failed: {fetch_res.error}",
                status_code=fetch_res.status_code or 0
            )
            return report

        self._log("RETRIEVE", f"Document retrieved successfully ({fetch_res.content_length} bytes, {fetch_res.latency_ms:.1f}ms).")

        # 2. Deterministic Analysis
        self._log("ANALYZE", "Executing deterministic HTML, metadata, headings, and schema inspections...")
        findings, metadata, perf_data = SEOAnalyzer.analyze(fetch_res, target_keyword)

        # 3. Scoring
        self._log("SCORE", "Computing explainable category scores and composite rating...")
        overall_score, tier, category_scores = SEOScoringEngine.score_audit(findings, is_local=False)

        # 4. Prioritization & Action Plan
        self._log("PRIORITIZE", "Ranking issues by severity and remediation impact...")
        prioritized_findings = SEOPrioritizer.prioritize_findings(findings)
        action_plan = SEOPrioritizer.generate_action_plan(prioritized_findings)

        # 5. Grounded AI Interpretation
        self._log("INTERPRET", "Synthesizing executive summary and grounded technical recommendations...")
        ai_recommendations = SEOAIInterpreter.interpret(
            target=fetch_res.final_url,
            overall_score=overall_score,
            tier=tier,
            category_scores=category_scores,
            findings=prioritized_findings,
            metadata=metadata,
            use_llm=use_llm
        )

        duration = time.time() - start_time
        self._log("COMPLETE", f"SEO Audit complete in {duration:.2f}s. Score: {overall_score:.1f}/100 ({tier.value}).")

        return SEOAuditReport(
            target=fetch_res.final_url,
            mode="url",
            target_keyword=target_keyword,
            overall_score=overall_score,
            tier=tier,
            summary=f"Analyzed {fetch_res.final_url}. Score: {overall_score:.1f}/100 ({tier.value}).",
            category_scores=category_scores,
            findings=prioritized_findings,
            action_plan=action_plan,
            ai_recommendations=ai_recommendations,
            performance_signals=perf_data,
            html_title=metadata.get("html_title", ""),
            meta_description=metadata.get("meta_description", ""),
            canonical_url=metadata.get("canonical_url"),
            h1_headings=metadata.get("h1_headings", []),
            word_count=metadata.get("word_count", 0),
            status_code=fetch_res.status_code or 200,
            timestamp=time.time()
        )

    def analyze_project(
        self,
        project_path: str,
        target_keyword: Optional[str] = None,
        use_llm: bool = True
    ) -> SEOAuditReport:
        """
        Runs an SEO audit on a local project codebase/template.
        """
        start_time = time.time()
        self._log("PROJECT", f"Scanning local project template at '{project_path}'...")

        fetch_res = SEOFetcher.read_local_project_html(project_path)
        if not fetch_res.success:
            self._log("ERROR", f"Local project read failed: {fetch_res.error}")
            return SEOAuditReport(
                target=project_path,
                mode="project",
                target_keyword=target_keyword,
                overall_score=0.0,
                tier=ScoreTier.NEEDS_IMPROVEMENT,
                summary=f"Project scan failed: {fetch_res.error}",
                status_code=404
            )

        self._log("ANALYZE", f"Analyzing template '{fetch_res.final_url}' ({fetch_res.content_length} bytes)...")
        findings, metadata, perf_data = SEOAnalyzer.analyze(fetch_res, target_keyword)

        self._log("SCORE", "Evaluating local template SEO health...")
        overall_score, tier, category_scores = SEOScoringEngine.score_audit(findings, is_local=True)

        prioritized_findings = SEOPrioritizer.prioritize_findings(findings)
        action_plan = SEOPrioritizer.generate_action_plan(prioritized_findings)

        self._log("INTERPRET", "Generating source-level SEO remediation guidance...")
        ai_recommendations = SEOAIInterpreter.interpret(
            target=fetch_res.final_url,
            overall_score=overall_score,
            tier=tier,
            category_scores=category_scores,
            findings=prioritized_findings,
            metadata=metadata,
            use_llm=use_llm
        )

        duration = time.time() - start_time
        self._log("COMPLETE", f"Local SEO Audit complete in {duration:.2f}s. Score: {overall_score:.1f}/100.")

        return SEOAuditReport(
            target=fetch_res.final_url,
            mode="project",
            target_keyword=target_keyword,
            overall_score=overall_score,
            tier=tier,
            summary=f"Local project audit for {fetch_res.final_url}. Score: {overall_score:.1f}/100 ({tier.value}).",
            category_scores=category_scores,
            findings=prioritized_findings,
            action_plan=action_plan,
            ai_recommendations=ai_recommendations,
            performance_signals=perf_data,
            html_title=metadata.get("html_title", ""),
            meta_description=metadata.get("meta_description", ""),
            canonical_url=metadata.get("canonical_url"),
            h1_headings=metadata.get("h1_headings", []),
            word_count=metadata.get("word_count", 0),
            status_code=200,
            timestamp=time.time()
        )

    @staticmethod
    def export_report_markdown(report: SEOAuditReport) -> str:
        """
        Renders a clean, comprehensive Markdown report for export or clipboard copy.
        """
        lines = [
            f"# 🌐 J.A.R.V.I.S. SEO Intelligence Report",
            f"",
            f"**Target**: `{report.target}`  ",
            f"**Overall Score**: **{report.overall_score:.1f}/100** ({report.tier.value if hasattr(report.tier, 'value') else str(report.tier)})  ",
            f"**Word Count**: {report.word_count} words | **Page Title**: `{report.html_title or 'Missing'}`  ",
            f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.timestamp))}",
            f"",
            f"> *Disclaimer*: {report.disclaimer}",
            f"",
            f"---",
            f"",
            f"## 📊 Category Breakdown",
            f"",
            f"| Category | Score | Weight | Passed | Warnings | Issues |",
            f"| :--- | :---: | :---: | :---: | :---: | :---: |"
        ]

        for cat_name, cs in report.category_scores.items():
            lines.append(f"| **{cat_name}** | **{cs.score:.1f}/100** | {int(cs.weight*100)}% | {cs.passed_count} | {cs.warning_count} | {cs.critical_count} |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 🛠️ What to Fix First (Action Plan)",
            f""
        ])

        if report.action_plan:
            for item in report.action_plan:
                lines.append(f"### {item.rank}. {item.title}")
                lines.append(f"- **Recommended Action**: {item.action}")
                lines.append(f"- **Impact**: `{item.impact}` | **Effort**: `{item.effort}` | **Category**: {item.category}")
                if item.why_it_matters:
                    lines.append(f"- **Why It Matters**: {item.why_it_matters}")
                lines.append("")
        else:
            lines.append("No critical issues detected. All baseline criteria satisfied!\n")

        if report.ai_recommendations:
            lines.extend([
                f"---",
                f"",
                f"## 🤖 AI Strategic Insights",
                f"",
                report.ai_recommendations,
                f""
            ])

        lines.extend([
            f"---",
            f"",
            f"## 🔍 Detailed Evidence-Based Findings",
            f""
        ])

        for f in report.findings:
            sev_str = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            cat_str = f.category.value if hasattr(f.category, "value") else str(f.category)
            lines.append(f"#### [{sev_str}] {f.title} ({cat_str})")
            if f.problem:
                lines.append(f"- **Problem**: {f.problem}")
            lines.append(f"- **Evidence**: {f.evidence} `[{f.evidence_type.value if hasattr(f.evidence_type, 'value') else str(f.evidence_type)}]`")
            if f.recommendation:
                lines.append(f"- **Recommendation**: {f.recommendation}")
            lines.append("")

        return "\n".join(lines)
