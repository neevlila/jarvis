"""
Master Idea Engine for J.A.R.V.I.S.
Coordinates stack analysis, generation, quality control, scoring, and ranking.
"""

import time
import hashlib
import json
from typing import Dict, Any, List, Optional, Callable

from idea_engine.models import (
    IdeaGenerationRequest,
    IdeaGenerationResult,
    StackAnalysis,
    ProjectIdea,
    GenerationMode,
    MasterPromptConfig,
    MasterBuildPrompt
)
from idea_engine.stack_analyzer import StackAnalyzer
from idea_engine.generator import IdeaGenerator
from idea_engine.quality_control import QualityControlEngine
from idea_engine.scoring import ScoringEngine
from idea_engine.prompt_engine import MasterPromptEngine


class IdeaEngine:
    """
    Authoritative Intelligence Engine for project concept generation, stack analysis,
    architectural feasibility ranking, and master build prompt synthesis.
    """

    def __init__(
        self,
        llm_callable: Optional[Callable[[str, str], str]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self._generator = IdeaGenerator(llm_callable=llm_callable)
        self._prompt_engine = MasterPromptEngine(log_callback=log_callback)
        self._log_callback = log_callback
        self._cache: Dict[str, IdeaGenerationResult] = {}
        self._session_ideas: Dict[str, ProjectIdea] = {}
        self._session_prompts: Dict[str, MasterBuildPrompt] = {}

    def _log(self, stage: str, message: str):
        print(f"[{stage}] {message}")
        if self._log_callback:
            try:
                self._log_callback(stage, message)
            except Exception:
                pass

    def generate_ideas(self, request: IdeaGenerationRequest) -> IdeaGenerationResult:
        """
        Runs the complete Idea Engine lifecycle:
        Input -> Stack Analysis -> Generation -> Quality Control -> Scoring -> Ranking.
        """
        start_time = time.time()
        tech_list = request.clean_technologies()

        self._log("IDEA_ENGINE", f"Input received: {len(tech_list)} technologies | Mode: {request.mode.value}")

        # Validate inputs based on mode
        if request.mode == GenerationMode.STACK_TO_IDEAS and not tech_list:
            return IdeaGenerationResult(
                success=False,
                mode=request.mode.value,
                stack_analysis=StackAnalysis(),
                error="Technology stack cannot be empty for Stack-to-Ideas generation."
            )

        if request.mode == GenerationMode.PROBLEM_TO_STACK and not request.problem_statement:
            return IdeaGenerationResult(
                success=False,
                mode=request.mode.value,
                stack_analysis=StackAnalysis(),
                error="Problem statement cannot be empty for Problem-to-Stack generation."
            )

        # Check Cache
        cache_key = self._make_cache_key(request)
        if cache_key in self._cache:
            self._log("IDEA_ENGINE", "Returning cached Idea Generation result.")
            return self._cache[cache_key]

        try:
            # 1. Stack Analysis & Capability Mapping
            self._log("STACK_ANALYZER", f"Analyzing technical capabilities of {len(tech_list)} technologies...")
            stack_analysis = StackAnalyzer.analyze(tech_list)
            self._log("STACK_ANALYZER", f"Found {len(stack_analysis.synergies)} cross-stack synergies.")

            # 2. Idea Generation via LLM
            self._log("IDEA_GENERATOR", f"Generating up to {request.number_of_ideas} project ideas...")
            raw_ideas = self._generator.generate(request, stack_analysis)
            self._log("IDEA_GENERATOR", f"Raw generation produced {len(raw_ideas)} candidate concepts.")

            # 3. Quality Control & Anti-Generic Filter
            self._log("QUALITY_CONTROL", "Running anti-generic and technology-forcing filters...")
            approved_ideas, rejections = QualityControlEngine.filter_ideas(raw_ideas)
            if rejections:
                for r in rejections:
                    self._log("QUALITY_CONTROL", f"Filtered: {r}")

            if not approved_ideas:
                # If all were filtered, fallback to raw ideas to avoid zero output
                approved_ideas = raw_ideas

            # 4. Scoring & Ranking
            self._log("SCORING", f"Calculating deterministic weighted scores for {len(approved_ideas)} ideas...")
            ranked_ideas = sorted(
                approved_ideas,
                key=lambda x: x.score.overall_score,
                reverse=True
            )

            top_idea = ranked_ideas[0] if ranked_ideas else None
            if top_idea:
                self._log("RANKING", f"Ranked {len(ranked_ideas)} ideas. Top idea: '{top_idea.title}' with score {top_idea.score.overall_score}/100 ({top_idea.score.tier.value})")

            # Store in session memory
            for idea in ranked_ideas:
                self._session_ideas[idea.id] = idea

            elapsed_ms = (time.time() - start_time) * 1000
            self._log("IDEA_ENGINE", f"Idea Generation completed in {elapsed_ms:.1f}ms.")

            result = IdeaGenerationResult(
                success=True,
                mode=request.mode.value,
                stack_analysis=stack_analysis,
                ideas=ranked_ideas,
                total_generated=len(ranked_ideas),
                top_recommendation=top_idea,
                execution_time_ms=elapsed_ms
            )

            self._cache[cache_key] = result
            return result

        except Exception as e:
            self._log("IDEA_ENGINE", f"Idea Generation encountered error: {str(e)}")
            elapsed_ms = (time.time() - start_time) * 1000
            return IdeaGenerationResult(
                success=False,
                mode=request.mode.value,
                stack_analysis=StackAnalyzer.analyze(tech_list),
                error=f"Idea generation failed: {str(e)}",
                execution_time_ms=elapsed_ms
            )

    def analyze_stack(self, technologies: List[str]) -> StackAnalysis:
        """Performs standalone stack capability mapping without full idea generation."""
        cleaned = [t.strip() for t in technologies if t.strip()]
        return StackAnalyzer.analyze(cleaned)

    def get_idea_by_id(self, idea_id: str) -> Optional[ProjectIdea]:
        """Retrieves a previously generated idea from session memory for deep inspection."""
        return self._session_ideas.get(idea_id)

    def generate_master_prompt(
        self,
        idea_id_or_obj: Any,
        config: Optional[MasterPromptConfig] = None
    ) -> MasterBuildPrompt:
        """
        Generates a production-grade 25+ section Master Build Specification for an idea.
        Accepts either an idea_id string or a ProjectIdea object.
        """
        if isinstance(idea_id_or_obj, str):
            idea = self.get_idea_by_id(idea_id_or_obj)
            if not idea:
                raise ValueError(f"Project Idea with ID '{idea_id_or_obj}' not found in active session.")
        elif isinstance(idea_id_or_obj, ProjectIdea):
            idea = idea_id_or_obj
        else:
            raise TypeError("Expected idea_id (str) or ProjectIdea object.")

        prompt = self._prompt_engine.generate_master_prompt(idea, config)
        self._session_prompts[prompt.prompt_id] = prompt
        return prompt

    def get_master_prompt(self, prompt_id: str) -> Optional[MasterBuildPrompt]:
        """Retrieves a previously generated Master Build Prompt from session memory."""
        return self._session_prompts.get(prompt_id)

    def get_prompt_for_idea(self, idea_id: str) -> Optional[MasterBuildPrompt]:
        """Finds the most recent Master Build Prompt generated for an idea."""
        for p in reversed(list(self._session_prompts.values())):
            if p.idea_id == idea_id:
                return p
        return None

    def improve_existing_project(
        self,
        title: str,
        technologies: List[str],
        features: List[str]
    ) -> IdeaGenerationResult:
        """Mode D: Evaluates an existing project and generates high-impact improvements."""
        req = IdeaGenerationRequest(
            technologies=technologies,
            mode=GenerationMode.PROJECT_IMPROVEMENTS,
            problem_statement=f"Improve existing project '{title}'",
            number_of_ideas=3,
            existing_project_details={
                "title": title,
                "stack": technologies,
                "features": features
            }
        )
        return self.generate_ideas(req)

    def _make_cache_key(self, request: IdeaGenerationRequest) -> str:
        data = {
            "tech": sorted([t.lower() for t in request.clean_technologies()]),
            "mode": request.mode.value,
            "problem": request.problem_statement or "",
            "difficulty": request.difficulty,
            "goal": request.goal,
            "domain": request.domain,
            "count": request.number_of_ideas
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
