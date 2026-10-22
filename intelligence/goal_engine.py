"""
Goal Decomposition Engine for J.A.R.V.I.S.

Recursively breaks down large user objectives into structured, dependency-ordered
task graphs (DAGs) and identifies the critical path and next executable tasks.
"""

import json
import re
from typing import Dict, List, Any, Optional, Callable, Set

from intelligence.models import GoalPlan, GoalTask, TaskPriority, TaskStatus
from providers.provider_manager import ProviderManager


class GoalDecompositionEngine:
    """
    Transforms broad high-level objectives into dependency-validated task plans.
    """

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

    CONTRADICTORY_PAIRS = [
        (
            [r"\boffline\b", r"\bair-?gapped\b", r"\blocal-?only\b", r"\bno internet\b"],
            [r"\breal-?time cloud sync\b", r"\bcloud stream\b", r"\bcloud database\b", r"\baws backend\b"],
            "Requirement specifies offline/air-gapped operation while simultaneously demanding real-time cloud synchronization.",
            "Choose either an offline-first architecture with optional deferred batch sync, or a fully connected cloud architecture."
        ),
        (
            [r"\bzero(?:-|\s+)(?:dependency|dependencies)\b", r"\bno external (?:packages|libraries)\b", r"\bstandard library only\b"],
            [r"\bpytorch\b", r"\btensorflow\b", r"\bdocker\b", r"\bkubernetes\b", r"\bfastapi\b"],
            "Zero-dependency constraint directly contradicts the inclusion of heavy third-party frameworks/libraries.",
            "Either permit necessary third-party package dependencies or implement a lightweight native Python algorithm."
        ),
        (
            [r"\bprivate\b", r"\bconfidential\b", r"\bsecret\b", r"\bzero telemetry\b"],
            [r"\bpublic(?:ly)? broadcast\b", r"\bpublish all data\b", r"\bpost to twitter\b", r"\bpublic dashboard\b"],
            "Strict privacy/confidentiality constraint contradicts public data broadcast.",
            "Implement an anonymization or selective redacting layer before public export, or keep all assets restricted to local access."
        ),
        (
            [r"\bread-?only\b", r"\bnon-?destructive\b"],
            [r"\bdelete\b", r"\bformat\b", r"\bdump database\b", r"\bwipe\b", r"\bdrop table\b"],
            "Non-destructive/read-only mode contradicts deletion or irreversible data wipe instructions.",
            "Use soft-deletion or dry-run simulation mode to inspect changes safely without data loss."
        )
    ]

    def detect_contradictions(self, goal: str) -> tuple[bool, List[str], Optional[str]]:
        """
        Scans user goal for mutually exclusive or impossible requirement pairs.
        """
        goal_lower = goal.lower()
        contradictions: List[str] = []
        recommendations: List[str] = []

        for group_a, group_b, explanation, rec in self.CONTRADICTORY_PAIRS:
            match_a = any(re.search(pat, goal_lower) for pat in group_a)
            match_b = any(re.search(pat, goal_lower) for pat in group_b)
            if match_a and match_b:
                contradictions.append(explanation)
                recommendations.append(rec)

        if contradictions:
            rec_str = " | ".join(recommendations)
            return True, contradictions, rec_str
        return False, [], None

    def decompose_goal_deterministic(self, goal: str) -> GoalPlan:
        """
        Deterministic task graph generator based on standard software engineering lifecycle.
        Guarantees instant, zero-network planning capability with contradiction awareness.
        """
        clean_goal = goal.strip()
        has_contra, contra_list, alt_rec = self.detect_contradictions(clean_goal)

        tasks: List[GoalTask] = []

        if has_contra:
            self._log("GOAL", f"WARNING: Contradictory goal detected: {contra_list[0]}")
            tasks.append(GoalTask(
                id="task-1",
                title="Architectural Conflict Resolution & Scope Clarification",
                description=f"Resolve identified architectural contradiction: {contra_list[0]} Recommendation: {alt_rec}",
                dependencies=[],
                priority=TaskPriority.CRITICAL,
                estimated_effort="1-2 hours",
                status=TaskStatus.PENDING,
                category="architecture"
            ))
            base_idx = 2
            prev_dep = "task-1"
        else:
            base_idx = 1
            prev_dep = None

        tasks.extend([
            GoalTask(
                id=f"task-{base_idx}",
                title=f"Requirements & Scope Specification for {clean_goal[:40]}",
                description="Define explicit functional requirements, user personas, API contracts, and success metrics.",
                dependencies=[prev_dep] if prev_dep else [],
                priority=TaskPriority.HIGH,
                estimated_effort="2-4 hours",
                status=TaskStatus.PENDING,
                category="requirements"
            ),
            GoalTask(
                id=f"task-{base_idx+1}",
                title="System Architecture & Database Schema Design",
                description="Design entity relationship model, database schema, data flow diagrams, and core interface abstractions.",
                dependencies=[f"task-{base_idx}"],
                priority=TaskPriority.HIGH,
                estimated_effort="3-5 hours",
                status=TaskStatus.PENDING,
                category="architecture"
            ),
            GoalTask(
                id=f"task-{base_idx+2}",
                title="Core Backend Services & Business Logic",
                description="Implement REST/GraphQL endpoints, business domain controllers, database migrations, and auth middleware.",
                dependencies=[f"task-{base_idx+1}"],
                priority=TaskPriority.HIGH,
                estimated_effort="6-10 hours",
                status=TaskStatus.PENDING,
                category="backend"
            ),
            GoalTask(
                id=f"task-{base_idx+3}",
                title="Frontend Interface & Client Integration",
                description="Build responsive user interface views, state management, client routing, and API integration hooks.",
                dependencies=[f"task-{base_idx+2}"],
                priority=TaskPriority.MEDIUM,
                estimated_effort="6-8 hours",
                status=TaskStatus.PENDING,
                category="frontend"
            ),
            GoalTask(
                id=f"task-{base_idx+4}",
                title="Security Hardening & Safety Validation",
                description="Implement rate-limiting, CORS configuration, input sanitization, CSRF tokens, and security audits.",
                dependencies=[f"task-{base_idx+2}"],
                priority=TaskPriority.HIGH,
                estimated_effort="2-4 hours",
                status=TaskStatus.PENDING,
                category="security"
            ),
            GoalTask(
                id=f"task-{base_idx+5}",
                title="Automated Unit & Integration Testing",
                description="Write unit test suites, mock service layers, and verify end-to-end user workflows.",
                dependencies=[f"task-{base_idx+3}", f"task-{base_idx+4}"],
                priority=TaskPriority.HIGH,
                estimated_effort="4-6 hours",
                status=TaskStatus.PENDING,
                category="testing"
            ),
            GoalTask(
                id=f"task-{base_idx+6}",
                title="Deployment & Release Verification",
                description="Package Docker container, configure environment secrets, deploy to target infrastructure, and verify health.",
                dependencies=[f"task-{base_idx+5}"],
                priority=TaskPriority.MEDIUM,
                estimated_effort="2-3 hours",
                status=TaskStatus.PENDING,
                category="devops"
            )
        ])

        critical_path = [t.id for t in tasks if t.category in ["architecture", "requirements", "backend", "frontend", "testing", "devops"]]
        return GoalPlan(
            goal=clean_goal,
            tasks=tasks,
            critical_path=critical_path,
            has_contradiction=has_contra,
            contradictions=contra_list,
            alternative_recommendation=alt_rec
        )

    def decompose_goal(
        self,
        goal: str,
        context_data: Optional[Dict[str, Any]] = None,
        use_llm: bool = True
    ) -> GoalPlan:
        """
        Decomposes user goal into a DAG task graph using LLM or deterministic fallback.
        """
        self._log("GOAL", f"Decomposing objective: '{goal}'...")
        has_contra, contra_list, alt_rec = self.detect_contradictions(goal)

        if not use_llm:
            plan = self.decompose_goal_deterministic(goal)
            self._log("GOAL", f"Generated deterministic plan with {len(plan.tasks)} tasks.")
            return plan

        prompt = f"""
You are the J.A.R.V.I.S. Goal Decomposition Engine.
Decompose the following high-level objective into an explicit, dependency-ordered Task Graph (DAG).

USER GOAL: {goal}
AVAILABLE CONTEXT: {json.dumps(context_data or {}, default=str)}

Rules:
1. Break into 5-9 concrete, non-redundant engineering tasks.
2. Dependencies must form a valid Directed Acyclic Graph (DAG) with NO circular references.
3. Earlier foundational tasks (e.g. schema, core backend) must be dependencies for downstream tasks (e.g. UI, testing).
4. Assign appropriate priorities (low, medium, high, critical).

Respond ONLY in valid JSON matching this schema:
{{
  "goal": "{goal}",
  "tasks": [
    {{
      "id": "task-1",
      "title": "Clear task title",
      "description": "Detailed actionable description",
      "dependencies": [],
      "priority": "high",
      "estimated_effort": "2-3 hours",
      "category": "architecture"
    }},
    {{
      "id": "task-2",
      "title": "Dependent task title",
      "description": "Actionable description",
      "dependencies": ["task-1"],
      "priority": "high",
      "estimated_effort": "4-5 hours",
      "category": "backend"
    }}
  ],
  "critical_path": ["task-1", "task-2"]
}}
"""
        try:
            raw_response = ProviderManager.chat(
                system_prompt="You are a senior software architect and project planner. Respond only in valid JSON.",
                messages_history=[],
                user_prompt=prompt,
                response_format_json=True
            )

            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\n?", "", clean_json)
                clean_json = re.sub(r"\n?```$", "", clean_json)

            parsed = json.loads(clean_json)

            raw_tasks = parsed.get("tasks", [])
            tasks: List[GoalTask] = []
            for t in raw_tasks:
                pri_str = str(t.get("priority", "medium")).lower()
                pri = TaskPriority(pri_str) if pri_str in [e.value for e in TaskPriority] else TaskPriority.MEDIUM
                tasks.append(GoalTask(
                    id=str(t.get("id", f"task-{len(tasks)+1}")),
                    title=str(t.get("title", "Untitled Task")),
                    description=str(t.get("description", "")),
                    dependencies=list(t.get("dependencies", [])),
                    priority=pri,
                    estimated_effort=str(t.get("estimated_effort", "1-2 hours")),
                    status=TaskStatus.PENDING,
                    category=str(t.get("category", "general"))
                ))

            # Validate DAG (break cycles if any exist)
            tasks = self._validate_and_sanitize_dag(tasks)
            critical_path = parsed.get("critical_path", [t.id for t in tasks])

            plan = GoalPlan(goal=goal, tasks=tasks, critical_path=critical_path)
            self._log("GOAL", f"Decomposition complete. Created DAG with {len(plan.tasks)} tasks.")
            return plan

        except Exception as e:
            self._log("GOAL", f"LLM goal decomposition failed: {e}. Falling back to deterministic plan.")
            return self.decompose_goal_deterministic(goal)

    def _validate_and_sanitize_dag(self, tasks: List[GoalTask]) -> List[GoalTask]:
        """
        Validates task graph dependencies. Eliminates self-dependencies,
        unknown dependency IDs, and circular dependency loops.
        """
        task_ids = {t.id for t in tasks}
        
        for task in tasks:
            # Remove unknown dependencies and self-dependencies
            task.dependencies = [d for d in task.dependencies if d in task_ids and d != task.id]

        # Topological cycle break check
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(tid: str, graph: Dict[str, List[str]]) -> bool:
            visited.add(tid)
            rec_stack.add(tid)
            for neighbor in graph.get(tid, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, graph):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(tid)
            return False

        dep_graph = {t.id: list(t.dependencies) for t in tasks}
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id, dep_graph):
                    # Break circular dependency on this task
                    task.dependencies = []
                    dep_graph[task.id] = []

        return tasks

    @staticmethod
    def get_next_actionable_task(plan: GoalPlan) -> Optional[GoalTask]:
        """
        Identifies the next ready task whose dependencies are all completed.
        """
        completed_ids = {t.id for t in plan.tasks if t.status == TaskStatus.COMPLETED}
        
        for task in plan.tasks:
            if task.status == TaskStatus.PENDING:
                all_deps_done = all(dep in completed_ids for dep in task.dependencies)
                if all_deps_done:
                    return task
        return None
