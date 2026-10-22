"""
AI Interpretation and Grounded Recommendation Engine for J.A.R.V.I.S. SEO Intelligence.

CRITICAL RULES:
- AI does NOT establish HTML facts (title exists, canonical exists, schema parses).
- AI interprets observed evidence and generates grounded developer recommendations.
- Validates AI response against hallucination constraints.
- Provides a robust deterministic fallback when LLM is unavailable or unconfigured.
"""

import json
from typing import Dict, List, Any, Optional
from llm_service import LLMService
from seo_engine.models import (
    SEOFinding,
    FindingSeverity,
    CategoryScore,
    ScoreTier
)


class SEOAIInterpreter:
    """
    Synthesizes evidence-grounded executive summaries and strategic action guidance.
    """

    SYSTEM_PROMPT = """You are J.A.R.V.I.S. Senior SEO Intelligence & Web Architecture Agent.
Your task is to analyze DETERMINISTIC EVIDENCE collected from an automated website audit and generate a high-precision, technical executive summary with actionable recommendations.

MANDATORY RULES:
1. Ground every statement strictly in the provided OBSERVED evidence and scores.
2. NEVER invent or hallucinate missing tags or findings not present in the evidence list.
3. NEVER make false SEO claims like "This change will rank #1 on Google" or "Guarantees top search placement".
4. Use professional, authoritative, evidence-based engineering language.
5. Provide specific, practical code snippets or structural fixes where helpful.

Response Format:
Return your response in clean, formatted Markdown with:
### 📊 Executive SEO Analysis
(2-3 paragraphs explaining the observed architectural strengths and primary technical bottlenecks)

### 🛠️ Strategic Remediation Plan
(Numbered technical steps focused on high-impact code changes)

### 💡 Content & Crawlability Insights
(Brief insights on information architecture, social sharing, and search engine discoverability)
"""

    @classmethod
    def interpret(
        cls,
        target: str,
        overall_score: float,
        tier: ScoreTier,
        category_scores: Dict[str, CategoryScore],
        findings: List[SEOFinding],
        metadata: Dict[str, Any],
        use_llm: bool = True
    ) -> str:
        """
        Synthesizes an evidence-grounded AI recommendation report, with deterministic fallback.
        """
        if not use_llm:
            return cls._build_deterministic_fallback(
                target, overall_score, tier, category_scores, findings, metadata
            )

        # Assemble evidence summary for LLM prompt
        non_passed = [f for f in findings if f.severity != FindingSeverity.PASSED]
        top_issues = non_passed[:8]

        evidence_payload = {
            "target": target,
            "overall_score": f"{overall_score:.1f}/100",
            "tier": tier.value if hasattr(tier, "value") else str(tier),
            "html_title": metadata.get("html_title", "N/A"),
            "meta_description": metadata.get("meta_description", "N/A"),
            "word_count": metadata.get("word_count", 0),
            "category_scores": {k: f"{v.score:.1f}/100" for k, v in category_scores.items()},
            "critical_and_high_issues": [
                {
                    "category": f.category.value if hasattr(f.category, "value") else str(f.category),
                    "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                    "problem": f.problem,
                    "evidence": f.evidence,
                    "recommendation": f.recommendation
                }
                for f in top_issues
            ]
        }

        user_prompt = f"Perform an SEO Intelligence interpretation for the following audit findings:\n```json\n{json.dumps(evidence_payload, indent=2)}\n```"

        try:
            raw_response = LLMService.query_llm_with_fallback(
                config=None,
                system_prompt=cls.SYSTEM_PROMPT,
                messages_history=[],
                user_prompt=user_prompt,
                response_format_json=False
            )

            if raw_response and len(raw_response.strip()) > 50:
                # Sanitize response: verify no prohibited claims
                sanitized = cls._sanitize_output(raw_response)
                return sanitized
            else:
                return cls._build_deterministic_fallback(
                    target, overall_score, tier, category_scores, findings, metadata
                )

        except Exception as e:
            # Fallback smoothly on API timeout or provider error
            return cls._build_deterministic_fallback(
                target, overall_score, tier, category_scores, findings, metadata
            )

    @classmethod
    def _sanitize_output(cls, text: str) -> str:
        """Removes exaggerated rank-guarantee claims if present in AI response."""
        prohibited = [
            (r"guarantee(?:s)?\s+(?:a\s+)?#1\s+rank(?:ing)?", "significantly improve search visibility"),
            (r"will\s+rank\s+#1\s+on\s+google", "may improve crawlability and search presentation"),
            (r"guarantees?\s+top\s+(?:page|rank)", "enhances organic search eligibility")
        ]
        import re
        sanitized = text
        for pat, repl in prohibited:
            sanitized = re.sub(pat, repl, sanitized, flags=re.IGNORECASE)
        return sanitized

    @classmethod
    def _build_deterministic_fallback(
        cls,
        target: str,
        overall_score: float,
        tier: ScoreTier,
        category_scores: Dict[str, CategoryScore],
        findings: List[SEOFinding],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Generates a rigorous deterministic summary without external LLM calls.
        """
        tier_str = tier.value if hasattr(tier, "value") else str(tier)
        critical_issues = [f for f in findings if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)]
        passed_checks = [f for f in findings if f.severity == FindingSeverity.PASSED]

        summary_lines = [
            "### 📊 Executive SEO Analysis",
            f"The target (`{target}`) achieved an overall SEO Intelligence score of **{overall_score:.1f}/100** ({tier_str} tier).",
            f"The audit observed **{len(passed_checks)} passing baseline checks** and identified **{len(critical_issues)} high-priority technical issues** requiring developer attention.",
            "",
            "### 🛠️ Strategic Remediation Plan"
        ]

        if critical_issues:
            for idx, issue in enumerate(critical_issues[:5], start=1):
                summary_lines.append(f"{idx}. **{issue.title}**: {issue.recommendation}")
                if issue.why_it_matters:
                    summary_lines.append(f"   *Impact*: {issue.why_it_matters}")
        else:
            summary_lines.append("1. **Maintain Core Standards**: Continue monitoring metadata and schema integrity on newly published pages.")
            summary_lines.append("2. **Performance Enhancements**: Optimize image compression and JavaScript delivery for faster TTFB.")

        summary_lines.extend([
            "",
            "### 💡 Content & Crawlability Insights",
            f"- Document Title: `{metadata.get('html_title') or 'Missing'}`",
            f"- Visible Content: {metadata.get('word_count', 0)} words analyzed across DOM elements.",
            f"- Technical Architecture: {category_scores.get('Technical SEO', CategoryScore(category=None, score=overall_score, weight=0.2)).score:.1f}/100 on technical baseline health."
        ])

        return "\n".join(summary_lines)
