"""
Automated Unit Tests for J.A.R.V.I.S. Intelligence Subsystem
Tests Self-Critique, Project Analyzer, Goal Decomposition,
Memory Engine, Skill Registry, Risk & Safety Engine,
Performance Intelligence, and Intelligence Coordinator.
"""

import unittest
import os
import tempfile
import json
import shutil

from intelligence.models import (
    CritiqueResult,
    CritiqueSeverity,
    FindingSeverity,
    TaskPriority,
    TaskStatus,
    MemoryType,
    RiskLevel,
    SkillPermission
)
from intelligence.critique import SelfCritiqueEngine
from intelligence.project_analyzer import ProjectAnalyzer
from intelligence.goal_engine import GoalDecompositionEngine
from intelligence.memory_engine import MemoryEngine
from intelligence.skill_engine import SkillRegistry, BaseSkill, SkillMetadata, SkillResult
from intelligence.risk_engine import RiskSafetyEngine
from intelligence.performance import PerformanceIntelligence
from intelligence.coordinator import IntelligenceCoordinator


class TestSelfCritiqueEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SelfCritiqueEngine()

    def test_valid_safe_content(self):
        content = "We recommend implementing a secure JWT authentication middleware with bcrypt password hashing."
        res = self.engine.evaluate_deterministic(content)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.severity, CritiqueSeverity.LOW)
        self.assertGreaterEqual(res.confidence, 0.7)

    def test_unsafe_destructive_pattern(self):
        destructive = "To fix this, run rm -rf / or drop database production;"
        res = self.engine.evaluate_deterministic(destructive)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.severity, CritiqueSeverity.CRITICAL)
        self.assertTrue(any("destructive" in issue.lower() for issue in res.issues))

    def test_empty_content(self):
        res = self.engine.evaluate_deterministic("")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.severity, CritiqueSeverity.HIGH)

    def test_generic_boilerplate_flagging(self):
        generic = "As an AI language model, I recommend considering many options before deciding."
        res = self.engine.evaluate_deterministic(generic)
        self.assertTrue(any("generic" in issue.lower() for issue in res.issues))


class TestProjectAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="jarvis_test_project_")
        self.analyzer = ProjectAnalyzer()

        # Create mock project files
        with open(os.path.join(self.temp_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write("import os\nfrom flask import Flask\napp = Flask(__name__)\n")

        with open(os.path.join(self.temp_dir, "vulnerable.py"), "w", encoding="utf-8") as f:
            f.write("import subprocess\nsubprocess.run('ls', shell=True)\napi_key = 'abcdef1234567890abcdef1234567890'\n")

        with open(os.path.join(self.temp_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("flask==2.3.2\nrequests>=2.28.0\n")

        os.makedirs(os.path.join(self.temp_dir, "tests"), exist_ok=True)
        with open(os.path.join(self.temp_dir, "tests", "test_app.py"), "w", encoding="utf-8") as f:
            f.write("def test_ok(): assert True\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_analyze_project_structure_and_health(self):
        report = self.analyzer.analyze_project(self.temp_dir)
        self.assertIn("Python", report.languages)
        self.assertIn("Flask", report.frameworks)
        self.assertIn("flask", report.dependencies)
        self.assertGreaterEqual(report.scores.overall, 40.0)
        self.assertLessEqual(report.scores.overall, 100.0)
        
        # Check security findings
        sec_findings = [f for f in report.findings if f.category == "security"]
        self.assertGreaterEqual(len(sec_findings), 1)
        self.assertTrue(any("shell=True" in f.problem for f in sec_findings))


class TestGoalDecompositionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GoalDecompositionEngine()

    def test_deterministic_decomposition(self):
        goal = "Build a microservice backend"
        plan = self.engine.decompose_goal_deterministic(goal)
        self.assertEqual(plan.goal, goal)
        self.assertGreaterEqual(len(plan.tasks), 5)
        self.assertTrue(len(plan.critical_path) > 0)

        # Check dependency ordering
        task_ids = {t.id for t in plan.tasks}
        for task in plan.tasks:
            for dep in task.dependencies:
                self.assertIn(dep, task_ids)
                self.assertNotEqual(dep, task.id)

    def test_actionable_task_retrieval(self):
        goal = "Test DAG Actionability"
        plan = self.engine.decompose_goal_deterministic(goal)
        
        # First actionable task should be task-1 (no dependencies)
        next_task = self.engine.get_next_actionable_task(plan)
        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.id, "task-1")

        # Mark task-1 completed, next should be task-2
        plan.tasks[0].status = TaskStatus.COMPLETED
        next_task_2 = self.engine.get_next_actionable_task(plan)
        self.assertEqual(next_task_2.id, "task-2")


class TestMemoryEngine(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        self.engine = MemoryEngine(storage_path=self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception:
                pass

    def test_store_and_retrieve(self):
        entry = self.engine.store(
            content="FastAPI is a modern high-performance Python web framework.",
            mem_type=MemoryType.SEMANTIC,
            source="test",
            confidence=0.98,
            tags=["fastapi", "python"]
        )
        self.assertIsNotNone(entry.id)
        
        results = self.engine.retrieve("FastAPI framework", type_filter=MemoryType.SEMANTIC)
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("FastAPI", results[0].content)

    def test_conflict_resolution_and_update(self):
        entry1 = self.engine.store(
            content="Database host is localhost:5432",
            mem_type=MemoryType.PROJECT,
            source="config",
            confidence=0.70
        )
        
        # Higher confidence evidence replaces
        entry2 = self.engine.store(
            content="Database host is postgres.internal:5432",
            mem_type=MemoryType.PROJECT,
            source="runtime_env",
            confidence=0.99
        )
        self.assertIn("postgres.internal", entry2.content)
        self.assertEqual(entry2.confidence, 0.99)

    def test_delete_memory(self):
        entry = self.engine.store(content="Temporary memory to delete", mem_type=MemoryType.TASK)
        deleted = self.engine.delete(entry.id)
        self.assertTrue(deleted)
        self.assertNotIn(entry.id, self.engine.entries)


class TestRiskSafetyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RiskSafetyEngine()

    def test_low_risk_action(self):
        assessment = self.engine.assess_risk("capture_screen")
        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertFalse(assessment.requires_confirmation)
        permitted, _ = self.engine.is_action_permitted(assessment)
        self.assertTrue(permitted)

    def test_high_risk_action(self):
        assessment = self.engine.assess_risk("delete_file", target="app/important.py")
        self.assertEqual(assessment.risk_level, RiskLevel.HIGH)
        self.assertTrue(assessment.requires_confirmation)
        permitted_no_auth, _ = self.engine.is_action_permitted(assessment, user_authorized=False)
        self.assertFalse(permitted_no_auth)
        permitted_with_auth, _ = self.engine.is_action_permitted(assessment, user_authorized=True)
        self.assertTrue(permitted_with_auth)

    def test_critical_risk_action(self):
        assessment = self.engine.assess_risk("execute_command", command_args=["format", "C:"])
        self.assertEqual(assessment.risk_level, RiskLevel.CRITICAL)
        self.assertTrue(assessment.requires_confirmation)
        permitted_no_auth, _ = self.engine.is_action_permitted(assessment, user_authorized=False)
        self.assertFalse(permitted_no_auth)


class TestPerformanceIntelligence(unittest.TestCase):
    def setUp(self):
        self.perf = PerformanceIntelligence()

    def test_record_metric_and_snapshot(self):
        self.perf.record_metric("decision_engine", 120.0, success=True)
        self.perf.record_metric("ocr_scan", 45.0, success=True)
        self.perf.record_metric("action_execute", 30.0, success=True)
        
        snapshot = self.perf.get_snapshot()
        self.assertEqual(snapshot.total_operations, 3)
        self.assertEqual(snapshot.tool_success_rate, 100.0)
        self.assertGreater(snapshot.avg_response_ms, 0.0)
        self.assertEqual(len(snapshot.anomalies), 0)

    def test_anomaly_detection_on_failures(self):
        for _ in range(4):
            self.perf.record_metric("llm_call", 9000.0, success=False)
        snapshot = self.perf.get_snapshot()
        self.assertGreater(len(snapshot.anomalies), 0)


class TestIntelligenceCoordinator(unittest.TestCase):
    def setUp(self):
        self.temp_mem_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        self.coordinator = IntelligenceCoordinator()
        self.coordinator.memory_engine.storage_path = self.temp_mem_file

    def tearDown(self):
        if os.path.exists(self.temp_mem_file):
            try:
                os.remove(self.temp_mem_file)
            except Exception:
                pass

    def test_coordinator_project_analysis_workflow(self):
        report = self.coordinator.analyze_project(".")
        self.assertIsNotNone(report)
        self.assertGreater(report.total_files, 0)
        
        # Verify knowledge was saved to memory
        mem_records = self.coordinator.memory_engine.retrieve("project architecture")
        self.assertGreaterEqual(len(mem_records), 1)

    def test_coordinator_goal_decomposition_workflow(self):
        plan = self.coordinator.decompose_goal("Develop scalable microservice", use_llm=False)
        self.assertGreaterEqual(len(plan.tasks), 5)
        
        snapshot = self.coordinator.get_performance_snapshot()
        self.assertGreater(snapshot.total_operations, 0)


if __name__ == '__main__':
    unittest.main()
