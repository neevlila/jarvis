"""
Quality Control and Anti-Generic Filtering for J.A.R.V.I.S. Idea Engine.
Prevents generic clones, filters duplicates, enforces technology-forcing rules, and validates idea completeness.
"""

from typing import List, Set, Tuple
import re
from idea_engine.models import ProjectIdea


class QualityControlEngine:
    """
    Validates generated project ideas against anti-generic rules, deduplication thresholds,
    and technology legitimacy constraints.
    """

    GENERIC_PATTERNS = [
        r"\b(?:basic|generic|simple)?\s*to-?do\s*(?:list|app|tracker)?\b",
        r"\b(?:basic|generic|simple)?\s*weather\s*(?:app|dashboard|widget)?\b",
        r"\b(?:basic|generic|simple)?\s*expense\s*tracker\b",
        r"\b(?:basic|generic|simple)?\s*note\s*taking\s*(?:app)?\b",
        r"\b(?:generic)?\s*ai\s*chat\s*bot\b",
        r"\b(?:generic)?\s*social\s*media\s*clone\b",
        r"\b(?:generic)?\s*e-?commerce\s*clone\b",
        r"\b(?:generic)?\s*recipe\s*(?:finder|app)\b"
    ]

    @classmethod
    def filter_ideas(
        cls,
        ideas: List[ProjectIdea],
        allowed_generic: bool = False
    ) -> Tuple[List[ProjectIdea], List[str]]:
        """
        Runs quality control passes over a list of candidate project ideas.
        Returns (approved_ideas, rejection_reasons).
        """
        approved: List[ProjectIdea] = []
        rejection_reasons: List[str] = []
        seen_titles: Set[str] = set()

        for idea in ideas:
            # 1. Structural completeness check
            if not idea.title or not idea.problem or not idea.solution or len(idea.core_features) < 2:
                rejection_reasons.append(f"Rejected '{idea.title}': Incomplete structure or insufficient core features.")
                continue

            # 2. Deduplication check (title / concept uniqueness)
            norm_title = re.sub(r"[^a-zA-Z0-9]", "", idea.title.lower())
            if norm_title in seen_titles:
                rejection_reasons.append(f"Rejected '{idea.title}': Duplicate or near-identical idea concept.")
                continue

            # 3. Anti-Generic check
            if not allowed_generic and cls.is_generic_idea(idea):
                rejection_reasons.append(f"Rejected '{idea.title}': Triggered anti-generic filter (generic clone/wrapper detected).")
                continue

            # 4. Technology-forcing check (every tech must have a distinct justified role)
            if not cls.validate_technology_roles(idea):
                rejection_reasons.append(f"Rejected '{idea.title}': Failed technology-forcing check (unjustified tech in stack).")
                continue

            seen_titles.add(norm_title)
            approved.append(idea)

        return approved, rejection_reasons

    @classmethod
    def is_generic_idea(cls, idea: ProjectIdea) -> bool:
        """Checks if the idea matches prohibited generic clone patterns."""
        combined_text = f"{idea.title} {idea.one_line_pitch} {idea.solution}".lower()

        # Check against banned generic patterns
        for pattern in cls.GENERIC_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                # Exception: if it incorporates heavy deep tech (like edge CV or multimodal reasoning), it might be legitimate
                has_deep_tech = any(
                    k in combined_text for k in ["computer vision", "multimodal", "pgvector", "edge iot", "autonomous", "real-time telemetry"]
                )
                if not has_deep_tech:
                    return True

        return False

    @classmethod
    def validate_technology_roles(cls, idea: ProjectIdea) -> bool:
        """
        Verifies that every technology mapped in the idea has a legitimate, non-empty role.
        """
        if not idea.technology_usage:
            return True  # If no tech usage mapped, pass structural check

        for mapping in idea.technology_usage:
            tech = mapping.technology.strip()
            role = mapping.role.strip()
            justification = mapping.justification.strip()

            if not tech or not role or not justification:
                return False

            # Ensure role is not just repeating the technology name
            if role.lower() == tech.lower():
                return False

        return True
