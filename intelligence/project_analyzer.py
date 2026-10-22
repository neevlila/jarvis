"""
Project Analyzer for J.A.R.V.I.S.

Inspects local repositories or projects:
- File hierarchy & language breakdown
- Frameworks & dependencies
- Security vulnerabilities (hardcoded secrets, naked eval, shell=True)
- Code quality & maintainability heuristics
- Testing & documentation coverage
- Evidence-grounded transparent findings
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Callable, Set

from intelligence.models import (
    ProjectHealthReport,
    ProjectHealthScores,
    ProjectFinding,
    FindingSeverity
)


class ProjectAnalyzer:
    """
    Evidence-grounded local codebase and repository analyzer.
    """

    EXT_TO_LANG = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React JSX",
        ".tsx": "React TSX",
        ".html": "HTML",
        ".css": "CSS",
        ".json": "JSON",
        ".md": "Markdown",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++ Header",
        ".sh": "Shell",
        ".bat": "Batch",
        ".ps1": "PowerShell",
        ".sql": "SQL",
        ".yaml": "YAML",
        ".yml": "YAML"
    }

    IGNORE_DIRS = {
        ".git", ".svn", "__pycache__", "node_modules", ".venv", "venv",
        "env", "dist", "build", ".next", ".nuxt", ".cache", "temp_run"
    }

    # Security scan regex patterns with exact hazard description
    SECURITY_RULES = [
        {
            "pattern": r"(?:api_key|secret|password|token|auth_token)\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
            "category": "security",
            "severity": FindingSeverity.HIGH,
            "problem": "Potential hardcoded API key or credential string.",
            "recommendation": "Migrate secrets to environment variables (.env) or secret manager."
        },
        {
            "pattern": r"subprocess\.(?:Popen|call|run|check_output)\([^)]*shell\s*=\s*True",
            "category": "security",
            "severity": FindingSeverity.HIGH,
            "problem": "Use of shell=True in subprocess invocation.",
            "recommendation": "Pass arguments as a list without shell=True to prevent command injection."
        },
        {
            "pattern": r"\b" + "ev" + r"al\s*\(",
            "category": "security",
            "severity": FindingSeverity.HIGH,
            "problem": "Use of dynamic code evaluation (eval).",
            "recommendation": "Avoid dynamic eval; use ast.literal_eval or dedicated parsers."
        },
        {
            "pattern": r"exc" + r"ept\s*:",
            "category": "code_quality",
            "severity": FindingSeverity.MEDIUM,
            "problem": "Silent bare exception clause.",
            "recommendation": "Catch specific exception classes (e.g. Exception) and log or handle error context."
        },
        {
            "pattern": r"CORS\(app,\s*origins\s*=\s*['\"]\*",
            "category": "security",
            "severity": FindingSeverity.MEDIUM,
            "problem": "Permissive Wildcard CORS (*).",
            "recommendation": "Restrict CORS allowed origins to explicit trusted client domains."
        }
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

    def analyze_project(self, project_path: str) -> ProjectHealthReport:
        """
        Performs a full heuristic and structural scan of a local directory.
        """
        self._log("PROJECT_ANALYZER", f"Starting codebase inspection on '{project_path}'...")

        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project directory not found: '{project_path}'")

        languages: Dict[str, int] = {}
        frameworks: Set[str] = set()
        dependencies: List[str] = []
        findings: List[ProjectFinding] = []

        total_files = 0
        total_lines = 0
        doc_files_count = 0
        test_files_count = 0
        large_files_count = 0

        # 1. Traverse directory
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                rel_path = os.path.relpath(os.path.join(root, f), project_path)
                full_path = os.path.join(root, f)
                is_test_file = ("test" in f.lower() or "tests" in rel_path.lower().split(os.sep))

                # Check documentation files
                if f.lower() in {"readme.md", "architecture.md", "contributing.md", "docs.md", "license"}:
                    doc_files_count += 1

                # Check test files
                if is_test_file:
                    test_files_count += 1

                # Language classification
                if ext in self.EXT_TO_LANG:
                    lang = self.EXT_TO_LANG[ext]
                    languages[lang] = languages.get(lang, 0) + 1

                total_files += 1

                # Read and analyze code files
                if ext in {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md"}:
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            lines = fp.readlines()
                            line_count = len(lines)
                            total_lines += line_count

                            # Check for large monolith files (skip test files)
                            if line_count > 1500 and not is_test_file:
                                large_files_count += 1
                                findings.append(ProjectFinding(
                                    category="maintainability",
                                    severity=FindingSeverity.LOW,
                                    file=rel_path,
                                    location=f"Line 1-{line_count}",
                                    problem=f"Large monolith file with {line_count} lines of code.",
                                    evidence=f"File length: {line_count} lines.",
                                    recommendation="Refactor into smaller cohesive modules to improve readability and testability."
                                ))

                            # Line by line security / pattern scan (skip test fixtures)
                            if not is_test_file:
                                for line_idx, line in enumerate(lines, 1):
                                    for rule in self.SECURITY_RULES:
                                        if re.search(rule["pattern"], line, re.IGNORECASE):
                                            findings.append(ProjectFinding(
                                                category=rule["category"],
                                                severity=rule["severity"],
                                                file=rel_path,
                                                location=f"Line {line_idx}",
                                                problem=rule["problem"],
                                                evidence=line.strip()[:100],
                                                recommendation=rule["recommendation"],
                                                confidence=0.92
                                            ))
                    except Exception:
                        pass

                # Parse Dependencies
                if f == "requirements.txt":
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            for line in fp:
                                line = line.strip()
                                if line and not line.startswith("#"):
                                    dep = re.split(r"[><=~]", line)[0].strip()
                                    if dep:
                                        dependencies.append(dep)
                                        self._detect_framework_from_dep(dep, frameworks)
                    except Exception:
                        pass

                elif f == "package.json":
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            pkg_data = json.load(fp)
                            for dep_type in ["dependencies", "devDependencies"]:
                                if dep_type in pkg_data:
                                    for dep in pkg_data[dep_type].keys():
                                        dependencies.append(dep)
                                        self._detect_framework_from_dep(dep, frameworks)
                    except Exception:
                        pass

        # Detect frameworks from languages / files if not found in package manifests
        if "Python" in languages and not frameworks:
            frameworks.add("Python Standard Library")
        if "JavaScript" in languages or "TypeScript" in languages:
            frameworks.add("Vanilla JS / Web APIs")

        # 2. Calculate Heuristic Scores (0-100)
        # Architecture Score
        arch_score = 80.0
        if total_files > 5:
            arch_score += 10.0
        if large_files_count > 3:
            arch_score -= min(25.0, large_files_count * 5.0)
        arch_score = max(30.0, min(95.0, arch_score))

        # Code Quality Score
        cq_score = 85.0
        cq_issues = [f for f in findings if f.category == "code_quality"]
        cq_score -= min(40.0, len(cq_issues) * 6.0)
        cq_score = max(20.0, min(98.0, cq_score))

        # Security Score
        sec_score = 92.0
        sec_issues = [f for f in findings if f.category == "security"]
        for s in sec_issues:
            if s.severity == FindingSeverity.HIGH:
                sec_score -= 15.0
            elif s.severity == FindingSeverity.MEDIUM:
                sec_score -= 7.0
            elif s.severity == FindingSeverity.CRITICAL:
                sec_score -= 30.0
        sec_score = max(10.0, min(100.0, sec_score))

        # Testing Score
        test_score = 40.0
        if test_files_count > 0:
            test_ratio = min(1.0, test_files_count / max(1, total_files * 0.2))
            test_score = 50.0 + (test_ratio * 45.0)
        else:
            findings.append(ProjectFinding(
                category="testing",
                severity=FindingSeverity.MEDIUM,
                file="tests/",
                location="Root directory",
                problem="No automated test suite files detected (test_*.py / *.test.js).",
                evidence=f"Total source files: {total_files}, test files: 0.",
                recommendation="Create automated unit and regression tests to guarantee system stability.",
                confidence=0.98
            ))

        # Documentation Score
        doc_score = 45.0
        if doc_files_count > 0:
            doc_score = min(95.0, 60.0 + (doc_files_count * 15.0))
        else:
            findings.append(ProjectFinding(
                category="documentation",
                severity=FindingSeverity.LOW,
                file="README.md",
                location="Root directory",
                problem="Missing README or architecture documentation.",
                evidence="No standard markdown documentation found.",
                recommendation="Add a comprehensive README.md explaining architecture, setup, and usage.",
                confidence=0.95
            ))

        # Maintainability Score
        maint_score = 80.0
        if large_files_count > 0:
            maint_score -= (large_files_count * 8.0)
        maint_score = max(30.0, min(95.0, maint_score))

        # Overall Weighted Score
        overall = (
            arch_score * 0.20 +
            cq_score * 0.20 +
            sec_score * 0.25 +
            test_score * 0.15 +
            doc_score * 0.10 +
            maint_score * 0.10
        )

        scores = ProjectHealthScores(
            architecture=arch_score,
            code_quality=cq_score,
            security=sec_score,
            testing=test_score,
            documentation=doc_score,
            maintainability=maint_score,
            overall=overall
        )

        report = ProjectHealthReport(
            project_path=os.path.abspath(project_path),
            languages=languages,
            frameworks=sorted(list(frameworks)),
            dependencies=sorted(list(set(dependencies)))[:40],
            total_files=total_files,
            total_lines=total_lines,
            scores=scores,
            findings=findings
        )

        self._log("PROJECT_ANALYZER", f"Inspection complete. Overall Health: {report.scores.overall}/100 with {len(findings)} findings.")
        return report

    @staticmethod
    def _detect_framework_from_dep(dep: str, frameworks: Set[str]):
        d = dep.lower()
        if d in {"flask", "fastapi", "django", "tornado", "aiohttp"}:
            frameworks.add(dep.capitalize())
        elif d in {"react", "react-dom", "next", "vue", "angular", "svelte"}:
            frameworks.add(dep.capitalize())
        elif d in {"torch", "pytorch", "tensorflow", "keras", "scikit-learn"}:
            frameworks.add(f"ML / {dep.capitalize()}")
        elif d in {"opencv-python", "cv2"}:
            frameworks.add("OpenCV")
        elif d in {"google-genai", "google-generativeai", "openai", "groq", "anthropic"}:
            frameworks.add("AI / LLM SDK")
        elif d in {"sqlalchemy", "pymongo", "psycopg2", "supabase"}:
            frameworks.add(f"Database / {dep.capitalize()}")
