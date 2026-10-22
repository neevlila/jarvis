"""
Skill & Plugin Architecture for J.A.R.V.I.S.

Provides a unified contract and discovery registry for modular skills:
- Idea Engine
- Project Analyzer
- Goal Decomposition
- Desktop Automation
- Code Assistant
- Email Assistant
- System Monitor
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable

from intelligence.models import (
    SkillMetadata,
    SkillPermission,
    RiskLevel,
    SkillResult
)


class BaseSkill(ABC):
    """
    Standard interface contract for all J.A.R.V.I.S. skills.
    """

    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata

    @abstractmethod
    def can_handle(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Returns confidence score (0.0 to 1.0) for handling the given user intent."""
        pass

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> SkillResult:
        """Executes the skill action."""
        pass


class SkillRegistry:
    """
    Central registry and permission enforcement gateway for skills.
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        self.skills: Dict[str, BaseSkill] = {}
        self.log_callback = log_callback

    def _log(self, stage: str, message: str):
        formatted = f"[{stage}] {message}"
        print(formatted)
        if self.log_callback:
            try:
                self.log_callback(stage, message)
            except Exception:
                pass

    def register_skill(self, skill: BaseSkill):
        """Registers a skill into the active registry."""
        self.skills[skill.metadata.name] = skill
        self._log("SKILL", f"Registered skill '{skill.metadata.name}' (Risk: {skill.metadata.risk_level.value}, Permissions: {[p.value for p in skill.metadata.permissions]})")

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        return self.skills.get(name)

    def list_skills(self) -> List[SkillMetadata]:
        return [skill.metadata for skill in self.skills.values()]

    def discover_skills(self, intent: str, context: Optional[Dict[str, Any]] = None) -> List[tuple[BaseSkill, float]]:
        """
        Evaluates registered skills against an intent string and returns ranked matches.
        """
        matches: List[tuple[BaseSkill, float]] = []
        for skill in self.skills.values():
            if not skill.metadata.enabled:
                continue
            confidence = skill.can_handle(intent, context)
            if confidence > 0.3:
                matches.append((skill, confidence))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def check_permissions(self, skill_name: str, granted_permissions: List[Any]) -> tuple[bool, str]:
        """
        Validates whether granted permissions satisfy the skill's required permissions.
        """
        skill = self.skills.get(skill_name)
        if not skill:
            return False, f"Skill '{skill_name}' not found."

        granted_set = set()
        for p in granted_permissions:
            if isinstance(p, SkillPermission):
                granted_set.add(p)
            elif isinstance(p, str):
                try:
                    granted_set.add(SkillPermission(p))
                except Exception:
                    pass

        missing = [p for p in skill.metadata.permissions if p not in granted_set]
        if missing:
            return False, f"Permission denied: Missing required permissions: {[p.value for p in missing]}"
        return True, "Permissions satisfied."

    def execute_skill(
        self,
        skill_name: str,
        context: Dict[str, Any],
        params: Dict[str, Any],
        granted_permissions: Optional[List[SkillPermission]] = None
    ) -> SkillResult:
        """
        Validates permissions and safely executes the requested skill.
        """
        skill = self.skills.get(skill_name)
        if not skill:
            return SkillResult(
                success=False,
                skill_name=skill_name,
                error=f"Skill '{skill_name}' not found in registry."
            )

        if not skill.metadata.enabled:
            return SkillResult(
                success=False,
                skill_name=skill_name,
                error=f"Skill '{skill_name}' is currently disabled."
            )

        # Permission check
        if granted_permissions is not None:
            missing = [p for p in skill.metadata.permissions if p not in granted_permissions]
            if missing:
                return SkillResult(
                    success=False,
                    skill_name=skill_name,
                    error=f"Unauthorized: Missing required permissions: {[p.value for p in missing]}"
                )

        start_time = time.time()
        self._log("SKILL", f"Executing skill '{skill_name}'...")
        try:
            res = skill.execute(context, params)
            res.execution_time_ms = (time.time() - start_time) * 1000
            self._log("SKILL", f"Skill '{skill_name}' completed in {res.execution_time_ms:.1f}ms (success={res.success}).")
            return res
        except Exception as e:
            exec_time = (time.time() - start_time) * 1000
            self._log("SKILL", f"Skill '{skill_name}' execution failed: {e}")
            return SkillResult(
                success=False,
                skill_name=skill_name,
                error=str(e),
                execution_time_ms=exec_time
            )


# ─────────────────────────────────────────────────────────────────────────────
# Built-In Skill Wrappers
# ─────────────────────────────────────────────────────────────────────────────

class IdeaEngineSkill(BaseSkill):
    def __init__(self, idea_engine_ref=None):
        meta = SkillMetadata(
            name="idea_engine",
            description="Generates, ranks, and evaluates project blueprints based on technology stack and goals.",
            inputs=["technologies", "mode", "problem_statement", "experience_level"],
            outputs=["ideas", "stack_analysis", "top_recommendation"],
            permissions=[SkillPermission.READ_FILES, SkillPermission.NETWORK],
            risk_level=RiskLevel.LOW
        )
        super().__init__(meta)
        self.idea_engine = idea_engine_ref

    def can_handle(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        low = intent.lower()
        if any(kw in low for kw in ["idea", "project idea", "what to build", "project recommendation", "generate ideas"]):
            return 0.95
        return 0.0

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> SkillResult:
        if not self.idea_engine:
            return SkillResult(success=False, skill_name=self.metadata.name, error="Idea Engine reference uninitialized.")
        try:
            from idea_engine import IdeaGenerationRequest, GenerationMode
            mode_str = params.get("mode", "stack_to_ideas")
            try:
                mode = GenerationMode(mode_str)
            except Exception:
                mode = GenerationMode.STACK_TO_IDEAS

            req = IdeaGenerationRequest(
                technologies=params.get("technologies", []),
                problem_statement=params.get("problem_statement"),
                mode=mode,
                experience_level=params.get("experience_level", "Intermediate"),
                project_type=params.get("project_type", "Portfolio Project"),
                time_available=params.get("time_available", "2 weeks")
            )
            res = self.idea_engine.generate_ideas(req)
            return SkillResult(success=True, skill_name=self.metadata.name, data=res.to_dict())
        except Exception as e:
            return SkillResult(success=False, skill_name=self.metadata.name, error=str(e))


class ProjectAnalyzerSkill(BaseSkill):
    def __init__(self, analyzer_ref=None):
        meta = SkillMetadata(
            name="project_analyzer",
            description="Deep local repository analysis, transparent health scoring, and evidence-grounded findings.",
            inputs=["project_path"],
            outputs=["scores", "languages", "findings", "dependencies"],
            permissions=[SkillPermission.READ_FILES],
            risk_level=RiskLevel.LOW
        )
        super().__init__(meta)
        self.analyzer = analyzer_ref

    def can_handle(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        low = intent.lower()
        if any(kw in low for kw in ["analyze project", "code quality", "security audit", "project health", "inspect codebase", "scan code"]):
            return 0.95
        return 0.0

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> SkillResult:
        if not self.analyzer:
            from intelligence.project_analyzer import ProjectAnalyzer
            self.analyzer = ProjectAnalyzer()
        try:
            path = params.get("project_path", ".")
            report = self.analyzer.analyze_project(path)
            return SkillResult(success=True, skill_name=self.metadata.name, data=report.to_dict())
        except Exception as e:
            return SkillResult(success=False, skill_name=self.metadata.name, error=str(e))


class GoalDecompositionSkill(BaseSkill):
    def __init__(self, goal_engine_ref=None):
        meta = SkillMetadata(
            name="goal_decomposition",
            description="Decomposes high-level objectives into dependency-validated DAG task plans.",
            inputs=["goal", "context"],
            outputs=["tasks", "critical_path"],
            permissions=[SkillPermission.NETWORK],
            risk_level=RiskLevel.LOW
        )
        super().__init__(meta)
        self.goal_engine = goal_engine_ref

    def can_handle(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        low = intent.lower()
        if any(kw in low for kw in ["break down", "decompose goal", "plan project", "create roadmap", "task graph"]):
            return 0.95
        return 0.0

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> SkillResult:
        if not self.goal_engine:
            from intelligence.goal_engine import GoalDecompositionEngine
            self.goal_engine = GoalDecompositionEngine()
        try:
            goal = params.get("goal", "Build modern application")
            use_llm = params.get("use_llm", True)
            plan = self.goal_engine.decompose_goal(goal, context, use_llm=use_llm)
            return SkillResult(success=True, skill_name=self.metadata.name, data=plan.to_dict())
        except Exception as e:
            return SkillResult(success=False, skill_name=self.metadata.name, error=str(e))


class SystemMonitorSkill(BaseSkill):
    def __init__(self):
        meta = SkillMetadata(
            name="system_monitor",
            description="Monitors host CPU, RAM, disk partitions, and active OS processes.",
            inputs=[],
            outputs=["cpu", "ram", "drives", "processes"],
            permissions=[SkillPermission.SYSTEM_CONTROL],
            risk_level=RiskLevel.LOW
        )
        super().__init__(meta)

    def can_handle(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        low = intent.lower()
        if any(kw in low for kw in ["system info", "cpu usage", "ram allocation", "memory usage", "disk space", "system status"]):
            return 0.90
        return 0.0

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> SkillResult:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory().percent
            drives = []
            for partition in psutil.disk_partitions():
                try:
                    if partition.mountpoint:
                        usage = psutil.disk_usage(partition.mountpoint)
                        drives.append({"device": partition.device.replace("\\", ""), "percent": usage.percent})
                except Exception:
                    pass
            return SkillResult(
                success=True,
                skill_name=self.metadata.name,
                data={"cpu": cpu, "ram": ram, "drives": drives}
            )
        except Exception as e:
            return SkillResult(success=False, skill_name=self.metadata.name, error=str(e))


class SEOSkill(BaseSkill):
    def __init__(self, seo_engine_ref=None):
        meta = SkillMetadata(
            name="seo_analyzer",
            description="Performs evidence-based technical SEO audits, explainable scoring, and prioritized remediation plans.",
            inputs=["url", "project_path", "target_keyword", "mode"],
            outputs=["overall_score", "tier", "category_scores", "findings", "action_plan", "ai_recommendations"],
            permissions=[SkillPermission.NETWORK, SkillPermission.READ_FILES],
            risk_level=RiskLevel.LOW
        )
        super().__init__(meta)
        self.seo_engine = seo_engine_ref

    def can_handle(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        low = intent.lower()
        if any(kw in low for kw in ["seo", "website audit", "seo score", "analyze website", "meta tags", "search optimization", "site audit"]):
            return 0.95
        return 0.0

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> SkillResult:
        if not self.seo_engine:
            from seo_engine.engine import SEOEngine
            self.seo_engine = SEOEngine()

        try:
            mode = params.get("mode", "url")
            keyword = params.get("target_keyword")
            use_llm = params.get("use_llm", True)

            if mode == "project" or params.get("project_path"):
                path = params.get("project_path", ".")
                report = self.seo_engine.analyze_project(path, target_keyword=keyword, use_llm=use_llm)
            else:
                url = params.get("url", "")
                if not url:
                    return SkillResult(success=False, skill_name=self.metadata.name, error="Missing required 'url' parameter for SEO audit.")
                report = self.seo_engine.analyze_url(url, target_keyword=keyword, use_llm=use_llm)

            return SkillResult(success=True, skill_name=self.metadata.name, data=report.to_dict())
        except Exception as e:
            return SkillResult(success=False, skill_name=self.metadata.name, error=str(e))

