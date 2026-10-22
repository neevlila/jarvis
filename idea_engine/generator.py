"""
Structured Idea Generator for J.A.R.V.I.S. Idea Engine.
Orchestrates AI prompt construction, schema enforcement, LLM execution via ProviderManager, and JSON parsing.
"""

import json
import re
import uuid
from typing import List, Dict, Any, Optional, Callable
from providers.provider_manager import ProviderManager
from idea_engine.models import (
    IdeaGenerationRequest,
    StackAnalysis,
    ProjectIdea,
    TechnologyMapping,
    DevelopmentPhase,
    GenerationMode
)
from idea_engine.scoring import ScoringEngine


class IdeaGenerator:
    """
    Constructs contextual prompts and translates LLM responses into structured ProjectIdea objects.
    """

    def __init__(self, llm_callable: Optional[Callable[[str, str], str]] = None):
        self._llm_callable = llm_callable

    def generate(
        self,
        request: IdeaGenerationRequest,
        stack_analysis: StackAnalysis
    ) -> List[ProjectIdea]:
        """
        Executes idea generation across Modes A, B, C, or D with automatic deterministic fallback.
        """
        system_prompt = self._build_system_prompt(request.mode)
        user_prompt = self._build_user_prompt(request, stack_analysis)

        raw_response = None
        try:
            if self._llm_callable:
                raw_response = self._llm_callable(system_prompt, user_prompt)
            else:
                raw_response = ProviderManager.chat(
                    system_prompt=system_prompt,
                    messages_history=[],
                    user_prompt=user_prompt,
                    response_format_json=True
                )
        except Exception as e:
            print(f"[IDEA_GENERATOR Warning] Live LLM provider unavailable ({e}). Activating deterministic architectural synthesis fallback...")
            return self._generate_deterministic_fallback_ideas(request, stack_analysis)

        try:
            parsed_data = self._parse_json_response(raw_response)
            ideas = self._transform_to_project_ideas(parsed_data, request)
            if ideas:
                return ideas
        except Exception as parse_e:
            print(f"[IDEA_GENERATOR Warning] Failed to parse LLM response ({parse_e}). Activating deterministic synthesis fallback...")

        return self._generate_deterministic_fallback_ideas(request, stack_analysis)

    def _build_system_prompt(self, mode: GenerationMode) -> str:
        base = (
            "You are J.A.R.V.I.S. Idea Engine, an expert AI Product & Software Architect. "
            "Your purpose is to design high-value, production-grade, technically deep project blueprints.\n\n"
            "CRITICAL RULES:\n"
            "1. NEVER generate generic clones (e.g. basic to-do apps, weather dashboards, simple CRUD apps, basic chatbot wrappers).\n"
            "2. PREVENT TECHNOLOGY FORCING: Every technology in the stack MUST have a clear, justified, technical responsibility.\n"
            "3. Ensure the project solves a tangible real-world problem with an identifiable target user.\n"
            "4. Provide realistic architecture, data flow, risks & mitigations, and development roadmaps.\n"
            "5. Respond ONLY with a valid, clean JSON array of project objects."
        )

        if mode == GenerationMode.PROBLEM_TO_STACK:
            base += "\nMode: PROBLEM -> RECOMMENDED STACK + PROJECT CONCEPTS. Recommend the ideal architecture and technologies for the given problem."
        elif mode == GenerationMode.STACK_AND_PROBLEM:
            base += "\nMode: STACK + PROBLEM -> COMPLETE PROJECT BLUEPRINT. Design an in-depth, production-ready solution tailored exactly to the problem and stack."
        elif mode == GenerationMode.PROJECT_IMPROVEMENTS:
            base += "\nMode: PROJECT IMPROVEMENTS. Analyze the existing project and propose high-impact architectural, AI, and feature upgrades."

        return base

    def _build_user_prompt(
        self,
        request: IdeaGenerationRequest,
        stack_analysis: StackAnalysis
    ) -> str:
        tech_list = request.clean_technologies()
        tech_str = ", ".join(tech_list) if tech_list else "Open / Recommended by J.A.R.V.I.S."
        synergies_str = "\n".join([f"- {s}" for s in stack_analysis.synergies]) if stack_analysis.synergies else "Standard modular integration"

        prompt = (
            f"=== USER CONSTRAINTS & CONTEXT ===\n"
            f"- Generation Mode: {request.mode.value}\n"
            f"- Input Tech Stack: {tech_str}\n"
            f"- Identified Stack Synergies:\n{synergies_str}\n"
            f"- Experience Level: {request.experience_level}\n"
            f"- Project Type: {request.project_type}\n"
            f"- Goal: {request.goal}\n"
            f"- Problem Domain: {request.domain}\n"
            f"- Available Time: {request.time_available}\n"
            f"- Budget: {request.budget}\n"
            f"- Target Difficulty: {request.difficulty}\n"
            f"- Number of Ideas to Generate: {request.number_of_ideas}\n"
        )

        if request.problem_statement:
            prompt += f"\n=== SPECIFIC PROBLEM STATEMENT ===\n{request.problem_statement}\n"

        if request.existing_project_details:
            prompt += f"\n=== EXISTING PROJECT DETAILS ===\n{json.dumps(request.existing_project_details, indent=2)}\n"

        prompt += (
            f"\n=== REQUIRED OUTPUT FORMAT ===\n"
            f"Output a raw JSON array containing exactly {request.number_of_ideas} objects matching this schema:\n"
            "[\n"
            "  {\n"
            '    "title": "Project Title",\n'
            '    "one_line_pitch": "Compelling single-sentence summary",\n'
            '    "problem": "Clear real-world problem being solved",\n'
            '    "target_users": ["Primary User Group A", "User Group B"],\n'
            '    "solution": "Technical solution description",\n'
            '    "core_features": ["Feature 1", "Feature 2", "Feature 3", "Feature 4"],\n'
            '    "technology_usage": [\n'
            '      {"technology": "Tech Name", "role": "Specific technical role", "justification": "Why this is optimal"}\n'
            "    ],\n"
            '    "architecture_summary": "Logical architecture (e.g. Frontend -> API -> AI Pipeline -> DB)",\n'
            '    "data_flow": ["1. User uploads data", "2. Backend validates & queues", "3. AI model runs inference", "4. Result saved & synced"],\n'
            '    "difficulty": "Easy / Medium / Hard / Advanced",\n'
            '    "estimated_time": "Estimated duration",\n'
            '    "why_this_stack": "Why this combination of technologies creates a competitive advantage",\n'
            '    "scores": {\n'
            '      "stack_compatibility": 95,\n'
            '      "feasibility": 90,\n'
            '      "real_world_value": 92,\n'
            '      "technical_depth": 88,\n'
            '      "innovation": 85,\n'
            '      "portfolio_value": 90\n'
            "    },\n"
            '    "risks": [\n'
            '      {"risk": "Specific technical or operational risk", "mitigation": "Concrete architectural mitigation"}\n'
            "    ],\n"
            '    "future_expansion": ["V2 capability 1", "V2 capability 2"],\n'
            '    "roadmap": [\n'
            '      {"phase_name": "Phase 1: Core MVP", "duration": "3 days", "key_tasks": ["Task 1", "Task 2"], "deliverables": ["Working API"]},\n'
            '      {"phase_name": "Phase 2: AI & Polish", "duration": "4 days", "key_tasks": ["Task 3"], "deliverables": ["Full App"]}\n'
            "    ]\n"
            "  }\n"
            "]\n"
            "Return ONLY the valid JSON array."
        )

        return prompt

    def _parse_json_response(self, raw_text: str) -> List[Dict[str, Any]]:
        """Parses and sanitizes LLM JSON output with error recovery strategies."""
        cleaned = raw_text.strip()

        # Strategy 1: Strip markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Strategy 2: Direct JSON parse
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # Handle wrapped format e.g. {"ideas": [...]} or {"projects": [...]}
                for key in ["ideas", "projects", "data", "results"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                return [parsed]
        except Exception:
            pass

        # Strategy 3: Regex JSON array search
        match = re.search(r"\[\s*\{.*\}\s*\]", raw_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass

        # Strategy 4: Regex single object search
        obj_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if obj_match:
            try:
                parsed = json.loads(obj_match.group(0))
                if isinstance(parsed, dict):
                    return [parsed]
            except Exception:
                pass

        raise ValueError(f"Failed to parse structured JSON array from LLM response. Raw response: {raw_text[:200]}")

    def _transform_to_project_ideas(
        self,
        raw_list: List[Dict[str, Any]],
        request: IdeaGenerationRequest
    ) -> List[ProjectIdea]:
        """Converts raw dictionary payloads into strongly-typed ProjectIdea models."""
        ideas: List[ProjectIdea] = []

        for item in raw_list:
            if not isinstance(item, dict):
                continue

            idea_id = f"idea_{uuid.uuid4().hex[:8]}"
            title = str(item.get("title", "Untitled Project Idea")).strip()
            pitch = str(item.get("one_line_pitch", "")).strip()
            problem = str(item.get("problem", "")).strip()
            target_users = item.get("target_users", ["General Users"])
            if isinstance(target_users, str):
                target_users = [target_users]

            solution = str(item.get("solution", "")).strip()
            core_features = item.get("core_features", [])
            if isinstance(core_features, str):
                core_features = [core_features]

            # Technology usage mapping
            tech_usage: List[TechnologyMapping] = []
            for t_item in item.get("technology_usage", []):
                if isinstance(t_item, dict):
                    tech_usage.append(TechnologyMapping(
                        technology=str(t_item.get("technology", "")),
                        role=str(t_item.get("role", "")),
                        justification=str(t_item.get("justification", ""))
                    ))

            # Scores calculation
            raw_scores = item.get("scores", {})
            score_breakdown = ScoringEngine.calculate_score(
                stack_compatibility=raw_scores.get("stack_compatibility", 85.0),
                feasibility=raw_scores.get("feasibility", 85.0),
                real_world_value=raw_scores.get("real_world_value", 85.0),
                technical_depth=raw_scores.get("technical_depth", 80.0),
                innovation=raw_scores.get("innovation", 80.0),
                portfolio_value=raw_scores.get("portfolio_value", 85.0)
            )

            # Risks
            raw_risks = item.get("risks") or item.get("risks_and_mitigations") or item.get("potential_risks") or item.get("technical_risks") or []
            if isinstance(raw_risks, str):
                raw_risks = [raw_risks]
            sanitized_risks = []
            if isinstance(raw_risks, list):
                for r in raw_risks:
                    if isinstance(r, dict):
                        r_name = str(r.get("risk") or r.get("title") or r.get("name") or "Technical Risk").strip()
                        r_mit = str(r.get("mitigation") or r.get("mitigate") or r.get("solution") or "Plan architectural validation.").strip()
                        sanitized_risks.append({"risk": r_name, "mitigation": r_mit})
                    elif isinstance(r, str) and r.strip():
                        if ":" in r:
                            parts = r.split(":", 1)
                            sanitized_risks.append({"risk": parts[0].strip(), "mitigation": parts[1].strip()})
                        elif " - " in r:
                            parts = r.split(" - ", 1)
                            sanitized_risks.append({"risk": parts[0].strip(), "mitigation": parts[1].strip()})
                        else:
                            sanitized_risks.append({"risk": r.strip(), "mitigation": "Follow architectural best practices."})
            if not sanitized_risks:
                sanitized_risks = [
                    {"risk": "Data throughput & latency bottlenecks", "mitigation": "Implement Redis queue buffering and database query indexing."},
                    {"risk": "Third-party service rate limits", "mitigation": "Apply client-side caching and exponential backoff retry strategies."}
                ]
            risks = sanitized_risks

            # Future Expansion
            raw_future = item.get("future_expansion") or item.get("future_scope") or item.get("future_features") or item.get("future_enhancements") or item.get("scalability") or []
            if isinstance(raw_future, str):
                raw_future = [raw_future]
            sanitized_future = []
            if isinstance(raw_future, list):
                for fe in raw_future:
                    if isinstance(fe, str) and fe.strip():
                        sanitized_future.append(fe.strip())
                    elif isinstance(fe, dict):
                        f_text = str(fe.get("feature") or fe.get("title") or fe.get("description") or "").strip()
                        if f_text:
                            sanitized_future.append(f_text)
            if not sanitized_future:
                sanitized_future = [
                    "Multi-tenant organization workspaces with granular role-based access control",
                    "Automated webhook integrations with Slack, Discord, and GitHub CI/CD",
                    "Predictive AI anomaly detection and telemetry forecasting models"
                ]
            future_expansion = sanitized_future

            # Roadmap
            roadmap: List[DevelopmentPhase] = []
            for phase in item.get("roadmap", []):
                if isinstance(phase, dict):
                    roadmap.append(DevelopmentPhase(
                        phase_name=str(phase.get("phase_name", "Phase")),
                        duration=str(phase.get("duration", "1 week")),
                        key_tasks=phase.get("key_tasks", []),
                        deliverables=phase.get("deliverables", [])
                    ))

            ideas.append(ProjectIdea(
                id=idea_id,
                title=title,
                one_line_pitch=pitch,
                problem=problem,
                target_users=target_users,
                solution=solution,
                core_features=core_features,
                technology_usage=tech_usage,
                architecture_summary=str(item.get("architecture_summary", "Modular Service Architecture")),
                data_flow=item.get("data_flow", []),
                difficulty=str(item.get("difficulty", request.difficulty)),
                estimated_time=str(item.get("estimated_time", request.time_available)),
                score=score_breakdown,
                risks=risks,
                future_expansion=item.get("future_expansion", []),
                roadmap=roadmap,
                why_this_stack=str(item.get("why_this_stack", ""))
            ))

        return ideas

    def _generate_deterministic_fallback_ideas(
        self,
        request: IdeaGenerationRequest,
        stack_analysis: StackAnalysis
    ) -> List[ProjectIdea]:
        """
        Generates robust, production-grade project blueprints deterministically
        when external LLM APIs are unreachable or rate-limited.
        """
        tech_list = request.clean_technologies() or ["Python", "FastAPI", "React", "Docker"]
        problem = request.problem_statement or ""
        domain = request.domain or "Enterprise & Developer Tools"

        # Build technology usage mappings
        tech_mappings = []
        for t in tech_list:
            t_lower = t.lower()
            if "react" in t_lower or "vue" in t_lower or "next" in t_lower or "html" in t_lower or "css" in t_lower:
                role = "Interactive Client Dashboard"
                just = f"Provides responsive component state management and real-time telemetry rendering using {t}."
            elif "fastapi" in t_lower or "flask" in t_lower or "django" in t_lower or "express" in t_lower or "nest" in t_lower or "node" in t_lower:
                role = "API & Core Event Router"
                just = f"Handles asynchronous request orchestration, data serialization, and backend workflows with {t}."
            elif "supabase" in t_lower or "postgres" in t_lower or "sql" in t_lower or "mongo" in t_lower or "redis" in t_lower:
                role = "Persistence & State Storage"
                just = f"Manages structured data schemas, indexing, and durable session state via {t}."
            elif "docker" in t_lower or "k8s" in t_lower or "kubernetes" in t_lower or "aws" in t_lower:
                role = "Containerization & Deployment"
                just = f"Enforces isolated microservice execution and streamlined CI/CD packaging with {t}."
            elif "gemini" in t_lower or "openai" in t_lower or "claude" in t_lower or "groq" in t_lower or "ai" in t_lower:
                role = "AI Reasoning & Structured Analysis"
                just = f"Extracts patterns, analyzes domain data, and generates structured recommendations using {t}."
            elif "python" in t_lower:
                role = "Core Computational Engine"
                just = f"Implements algorithms, data processing, and backend logic with {t}."
            else:
                role = "Specialized Module Utility"
                just = f"Integrates domain capabilities directly into the application pipeline."

            tech_mappings.append(TechnologyMapping(
                technology=t,
                role=role,
                justification=just
            ))

        # Synthesize 3 tailored project concepts
        concepts = []

        if problem:
            # Mode B or Mode C: Direct Solution to the problem
            concepts.append({
                "title": f"Nexus: Automated {problem[:30].strip().title()} Hub",
                "pitch": f"High-performance automated solution directly addressing {problem.lower()} using {', '.join(tech_list[:3])}.",
                "problem": problem,
                "solution": f"Modular, event-driven architecture designed to resolve '{problem}' through structured automated pipelines.",
                "features": [
                    f"Automated analysis pipeline resolving {problem[:40]}",
                    "Real-time status monitor with visual telemetry charts",
                    "Role-based access control and encrypted configuration management",
                    "Automated audit logging and actionable error recovery triggers"
                ]
            })
            concepts.append({
                "title": f"Pulse: Real-Time Intelligence & Diagnostic Core",
                "pitch": f"Continuous monitoring and predictive analysis system for {domain.lower()}.",
                "problem": f"Lack of real-time visibility and high latency when diagnosing issues in {domain.lower()}.",
                "solution": "High-throughput asynchronous event ingestion with instant heuristic anomaly detection.",
                "features": [
                    "Sub-100ms event processing and stream aggregation",
                    "Interactive network and component topology graph",
                    "Historical regression telemetry and metric forecasting",
                    "One-click remediation and policy deployment"
                ]
            })
            concepts.append({
                "title": f"Forge: Autonomous Workflow & Automation Engine",
                "pitch": f"Extensible workflow automation platform leveraging {', '.join(tech_list[:2])}.",
                "problem": f"Repetitive manual operations causing operational bottlenecks in {domain.lower()}.",
                "solution": "Composable task DAG engine with deterministic execution gates and safety validation.",
                "features": [
                    "Visual DAG workflow builder with dependency resolution",
                    "Deterministic validation gate preventing destructive operations",
                    "Automated webhook integrations and notification dispatch",
                    "Detailed execution trace logs with replay capabilities"
                ]
            })
        else:
            # Mode A: Stack to Ideas
            concepts.append({
                "title": f"Sentinel: Autonomous {domain.split()[0]} Command Center",
                "pitch": f"Production-grade control hub and telemetry engine built with {', '.join(tech_list[:3])}.",
                "problem": f"Operational visibility and data fragmentation across disparate tools in {domain.lower()}.",
                "solution": f"Unified, high-density dashboard integrating backend services into a single pane of glass.",
                "features": [
                    "Unified real-time metrics and state visualization",
                    "Automated health checks and heuristic anomaly alerts",
                    "Secure role-based API contracts with strict schema validation",
                    "Containerized multi-environment configuration support"
                ]
            })
            concepts.append({
                "title": f"VectorCraft: Semantic Knowledge & Intelligence Engine",
                "pitch": f"Intelligent data extraction, indexing, and search platform powered by {tech_list[0] if tech_list else 'Python'}.",
                "problem": "Unstructured domain documentation and records are difficult to query and synthesize accurately.",
                "solution": "Hybrid keyword and semantic retrieval engine with structured validation and confidence scoring.",
                "features": [
                    "Multi-format document ingestion and parsing pipeline",
                    "Fast vector indexing with confidence-based conflict resolution",
                    "Interactive query console with citation grounding",
                    "Automated sync and backup persistence"
                ]
            })
            concepts.append({
                "title": f"FlowStream: High-Throughput Event Orchestrator",
                "pitch": f"Asynchronous event processing and task automation grid built with {', '.join(tech_list[:2])}.",
                "problem": "High-concurrency data streams create memory pressure and unhandled failure cascades.",
                "solution": "Resilient, decoupled microservice grid with backpressure management and automated retries.",
                "features": [
                    "Asynchronous worker pool with priority scheduling",
                    "Dead-letter queue inspection and failure triage",
                    "Live throughput graphs and bottleneck diagnostics",
                    "End-to-end execution tracing with millisecond precision"
                ]
            })

        ideas: List[ProjectIdea] = []
        for idx, c in enumerate(concepts, 1):
            score = ScoringEngine.calculate_score(
                stack_compatibility=92.0 - (idx * 2),
                feasibility=90.0,
                real_world_value=93.0 - (idx * 1.5),
                technical_depth=88.0 + idx,
                innovation=87.0 + idx,
                portfolio_value=91.0
            )

            roadmap = [
                DevelopmentPhase(
                    phase_name="Foundation & Architecture",
                    duration="Week 1",
                    key_tasks=["Scaffold project repository and design tokens", "Configure API routers and data models", "Set up containerization and dev environment"],
                    deliverables=["Working base service with schema validation", "Docker compose environment"]
                ),
                DevelopmentPhase(
                    phase_name="Core Capabilities & Logic",
                    duration="Week 2",
                    key_tasks=["Implement core processing pipeline", "Build interactive dashboard UI", "Wire API integration endpoints"],
                    deliverables=["Functional end-to-end user workflows", "Interactive UI controls"]
                ),
                DevelopmentPhase(
                    phase_name="Testing, Polish & Hardening",
                    duration="Week 3",
                    key_tasks=["Implement automated unit & integration test suite", "Enforce security policies and input sanitization", "Optimize runtime bundle and query latency"],
                    deliverables=["Production-ready MVP with 100% test coverage", "Complete documentation"]
                )
            ]

            risks = [
                {"risk": "High concurrency data throughput peaks", "mitigation": "Implement Redis queue buffering and exponential backoff retry policies."},
                {"risk": "Malformed third-party input payloads", "mitigation": "Enforce strict schema validation and error boundaries on all endpoints."}
            ]

            future = [
                "Multi-tenant organization workspaces with granular RBAC",
                "Automated webhook integrations with Slack, Discord, and GitHub",
                "Predictive anomaly detection and time-series forecasting"
            ]

            arch_summary = " -> ".join(tech_list[:4]) + " (Decoupled Modular Architecture)"

            ideas.append(ProjectIdea(
                id=f"idea_{uuid.uuid4().hex[:8]}",
                title=c["title"],
                one_line_pitch=c["pitch"],
                problem=c["problem"],
                target_users=["Software Engineers", "DevOps Teams", "Product Architects", "Enterprise Users"],
                solution=c["solution"],
                core_features=c["features"],
                technology_usage=tech_mappings,
                architecture_summary=arch_summary,
                data_flow=[
                    "1. Client triggers action request -> Ingested by API Router",
                    "2. Backend validates request payload against schema contracts",
                    "3. Core computational engine processes task and stores results in persistence layer",
                    "4. Real-time updates dispatched to UI with sub-second latency"
                ],
                difficulty=request.difficulty,
                estimated_time=request.time_available,
                score=score,
                risks=risks,
                future_expansion=future,
                roadmap=roadmap,
                why_this_stack=f"The combination of {', '.join(tech_list)} provides the optimal balance of development velocity, computational performance, and production scalability."
            ))

        return ideas

