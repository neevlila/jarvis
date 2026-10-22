"""
Self-Critique Engine for J.A.R.V.I.S.

Evaluates important J.A.R.V.I.S. decisions, plans, or generated answers before
they are returned or executed. Detects unsupported assumptions, contradictions,
missing information, unsafe recommendations, and low confidence.
"""

import json
import re
from typing import Dict, Any, Optional, List, Callable

from intelligence.models import CritiqueResult, CritiqueSeverity
from providers.provider_manager import ProviderManager


class SelfCritiqueEngine:
    """
    Quality gate and reflective critique engine.
    Ensures answers and action decisions satisfy safety, consistency, and goal criteria.
    """

    UNSAFE_PATTERNS = [
        r"rm\s+-rf\s+[/~]",
        r"drop\s+database",
        r"drop\s+table",
        r"truncate\s+table",
        r"format\s+[c-z]:",
        r"del\s+/[fqs]\s+[c-z]:\\windows",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # Fork bomb
        r"chmod\s+-r\s+777\s+/",
        r"sudo\s+rm",
        r"delete\s+production"
    ]

    GENERIC_PATTERNS = [
        r"as an ai (language model|assistant)",
        r"i am only an ai",
        r"it is important to consider all aspects",
        r"consult a professional"
    ]

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        self.log_callback = log_callback

    def _log(self, stage: str, message: str):
        formatted = f"[{stage}] {message}"
        print(formatted)
        if self.log_callback:
            try:
                self.log_callback(stage, message)
            except Exception:
                pass

    def evaluate_deterministic(
        self,
        candidate_content: str,
        context_data: Optional[Dict[str, Any]] = None,
        user_goal: Optional[str] = None
    ) -> CritiqueResult:
        """
        Fast deterministic heuristic evaluation without requiring LLM calls.
        """
        issues: List[str] = []
        missing_info: List[str] = []
        assumptions: List[str] = []
        risks: List[str] = []
        recommended_changes: List[str] = []
        severity = CritiqueSeverity.LOW
        confidence = 0.90

        content_lower = candidate_content.lower()

        # 1. Check for empty or too short content
        if not candidate_content or len(candidate_content.strip()) < 5:
            issues.append("Candidate content is empty or excessively brief.")
            severity = CritiqueSeverity.HIGH
            confidence = 0.20

        # 2. Check for unsafe / destructive commands
        for pattern in self.UNSAFE_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                issues.append(f"Potentially destructive system pattern detected matching: '{pattern}'.")
                risks.append("Command could lead to irreversible data loss or system corruption.")
                recommended_changes.append("Require explicit user confirmation or replace with non-destructive alternative.")
                severity = CritiqueSeverity.CRITICAL
                confidence = 0.30

        # 3. Check for generic cop-out responses
        for pattern in self.GENERIC_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                issues.append("Response contains generic AI boilerplate phrasing.")
                recommended_changes.append("Provide concrete, direct technical guidance instead of AI disclaimers.")
                if severity == CritiqueSeverity.LOW:
                    severity = CritiqueSeverity.MEDIUM

        # 4. Check goal alignment if user_goal is provided
        if user_goal:
            goal_keywords = [w.lower() for w in re.findall(r"\b\w{4,}\b", user_goal) if w.lower() not in {"what", "how", "make", "build", "please", "with", "this", "that", "from", "your"}]
            found_keywords = [kw for kw in goal_keywords if kw in content_lower or (len(kw) > 4 and kw[:4] in content_lower)]
            if goal_keywords and len(found_keywords) == 0:
                missing_info.append("Candidate does not directly address key subject terms from user goal.")
                issues.append("Possible goal misalignment.")
                confidence = max(0.50, confidence - 0.20)
                if severity == CritiqueSeverity.LOW:
                    severity = CritiqueSeverity.MEDIUM

        # 5. Check context consistency
        if context_data:
            known_stack = context_data.get("technologies", [])
            for tech in known_stack:
                if tech.lower() not in content_lower and len(known_stack) <= 3:
                    assumptions.append(f"Content does not explicitly leverage declared technology: '{tech}'.")

        is_valid = (severity in [CritiqueSeverity.LOW, CritiqueSeverity.MEDIUM]) and not any("destructive" in r.lower() or "irreversible" in r.lower() for r in risks)

        return CritiqueResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            missing_information=missing_info,
            assumptions=assumptions,
            risks=risks,
            recommended_changes=recommended_changes,
            severity=severity,
            revised_content=None,
            iterations_used=1
        )

    def critique(
        self,
        candidate_content: str,
        context_data: Optional[Dict[str, Any]] = None,
        user_goal: Optional[str] = None,
        use_llm: bool = False,
        max_revisions: int = 2
    ) -> CritiqueResult:
        """
        Runs comprehensive critique. If deterministic checks fail or use_llm is enabled,
        generates structured critique and revision.
        """
        self._log("CRITIQUE", "Evaluating candidate content against reasoning and safety criteria...")
        
        # Fast heuristic pass
        det_result = self.evaluate_deterministic(candidate_content, context_data, user_goal)
        
        if det_result.is_valid and not use_llm:
            self._log("CRITIQUE", f"Candidate APPROVED. Confidence: {det_result.confidence} | Severity: {det_result.severity.value}")
            return det_result

        # If heuristic is valid and use_llm is false, return
        if not use_llm:
            self._log("CRITIQUE", f"Candidate flagged with {len(det_result.issues)} issues. Severity: {det_result.severity.value}")
            return det_result

        # LLM-assisted Deep Critique and Revision
        current_content = candidate_content
        iterations = 0
        final_result = det_result

        while iterations < min(max_revisions, 3):
            iterations += 1
            self._log("CRITIQUE", f"Running LLM deep critique iteration {iterations}/{max_revisions}...")

            prompt = f"""
You are the J.A.R.V.I.S. Self-Critique Engine.
Evaluate the following candidate response or decision objectively.

USER GOAL: {user_goal or 'N/A'}
CONTEXT: {json.dumps(context_data or {}, default=str)}
CANDIDATE CONTENT:
\"\"\"{current_content}\"\"\"

Evaluation Questions:
1. Is the conclusion supported by available evidence?
2. Did J.A.R.V.I.S. assume something that was not observed?
3. Is important context missing?
4. Does the proposed action satisfy the user's goal?
5. Is the action safe?
6. Is there a simpler alternative?
7. Is confidence justified?

Respond ONLY in valid JSON matching this exact schema:
{{
  "is_valid": true,
  "confidence": 0.88,
  "issues": ["list of concrete reasoning/safety issues if any"],
  "missing_information": ["list of missing facts"],
  "assumptions": ["list of unverified assumptions"],
  "risks": ["list of hazards or side-effects"],
  "recommended_changes": ["concrete improvements"],
  "severity": "low",
  "revised_content": "improved revision of content, or null if already valid"
}}
"""
            try:
                raw_response = ProviderManager.chat(
                    system_prompt="You are a strict, objective, precision-driven AI critique evaluator. Respond only in valid JSON.",
                    messages_history=[],
                    user_prompt=prompt,
                    response_format_json=True
                )
                
                # Clean markdown backticks if any
                clean_json = raw_response.strip()
                if clean_json.startswith("```"):
                    clean_json = re.sub(r"^```(?:json)?\n?", "", clean_json)
                    clean_json = re.sub(r"\n?```$", "", clean_json)

                parsed = json.loads(clean_json)

                sev_str = str(parsed.get("severity", "low")).lower()
                severity = CritiqueSeverity(sev_str) if sev_str in [e.value for e in CritiqueSeverity] else CritiqueSeverity.LOW

                final_result = CritiqueResult(
                    is_valid=bool(parsed.get("is_valid", True)),
                    confidence=float(parsed.get("confidence", 0.85)),
                    issues=parsed.get("issues", []),
                    missing_information=parsed.get("missing_information", []),
                    assumptions=parsed.get("assumptions", []),
                    risks=parsed.get("risks", []),
                    recommended_changes=parsed.get("recommended_changes", []),
                    severity=severity,
                    revised_content=parsed.get("revised_content"),
                    iterations_used=iterations
                )

                if final_result.is_valid or not final_result.revised_content:
                    break
                
                # Adopt revised content for next iteration check
                current_content = final_result.revised_content

            except Exception as e:
                self._log("CRITIQUE", f"LLM critique call encountered exception: {e}. Falling back to deterministic analysis.")
                final_result.iterations_used = iterations
                break

        self._log("CRITIQUE", f"Critique complete. Valid: {final_result.is_valid} | Confidence: {final_result.confidence}")
        return final_result
