import unittest
from idea_engine.stack_analyzer import StackAnalyzer


class TestStackAnalyzer(unittest.TestCase):
    def test_canonicalize_name(self):
        self.assertEqual(StackAnalyzer.canonicalize_name("py"), "python")
        self.assertEqual(StackAnalyzer.canonicalize_name("postgres"), "postgresql")
        self.assertEqual(StackAnalyzer.canonicalize_name("reactjs"), "react")
        self.assertEqual(StackAnalyzer.canonicalize_name("gemini"), "gemini api")

    def test_get_profile_known_and_unknown(self):
        py_prof = StackAnalyzer.get_profile("Python")
        self.assertIsNotNone(py_prof)
        self.assertEqual(py_prof.category, "Language")
        self.assertTrue(len(py_prof.primary_capabilities) > 0)
        self.assertIn("Backend APIs", py_prof.primary_capabilities)

        unk_prof = StackAnalyzer.get_profile("CustomToolXYZ")
        self.assertIsNotNone(unk_prof)
        self.assertEqual(unk_prof.category, "Specialized Tool / Library")

    def test_stack_analysis_synergies(self):
        analysis = StackAnalyzer.analyze(["Python", "FastAPI", "PostgreSQL", "Docker"])
        self.assertTrue(len(analysis.synergies) > 0)
        self.assertTrue(any("FastAPI" in s for s in analysis.synergies))
        self.assertIn("Language", analysis.categories_present)
        self.assertIn("Backend Framework", analysis.categories_present)
        self.assertIn("Relational Database", analysis.categories_present)
        self.assertIn("DevOps & Containerization", analysis.categories_present)

    def test_missing_layers_detection(self):
        # Frontend-only stack
        analysis = StackAnalyzer.analyze(["React", "Tailwind CSS"])
        self.assertIn("Backend Framework", analysis.missing_categories)
        self.assertIn("Relational Database", analysis.missing_categories)

    def test_ai_stack_synergies(self):
        analysis = StackAnalyzer.analyze(["Python", "PyTorch", "OpenCV", "Gemini API"])
        self.assertTrue(any("Vision" in s or "Multimodal" in s for s in analysis.synergies))
        self.assertIn("AI / Multimodal Foundation Model", analysis.categories_present)
        self.assertIn("Computer Vision", analysis.categories_present)


if __name__ == "__main__":
    unittest.main()
