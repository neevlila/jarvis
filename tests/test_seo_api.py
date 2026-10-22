"""
API and Endpoint tests for SEO REST services in buddy.py.
"""

import unittest
import json
import buddy


class TestSEOAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        buddy.app.config['TESTING'] = True
        cls.client = buddy.app.test_client()
        cls.auth_headers = {
            'Content-Type': 'application/json',
            'X-JARVIS-Auth': buddy.api_token
        }

        # Initialize mock or dummy assistant_ref if not running
        if not buddy.assistant_ref:
            class DummyAssistant:
                def __init__(self):
                    from seo_engine.engine import SEOEngine
                    from intelligence.coordinator import IntelligenceCoordinator
                    self.seo_engine = SEOEngine()
                    self.intelligence = IntelligenceCoordinator(seo_engine_ref=self.seo_engine)
            buddy.assistant_ref = DummyAssistant()

    def test_unauthorized_access(self):
        resp = self.client.post('/api/seo/analyze', json={'url': 'https://example.com'})
        self.assertEqual(resp.status_code, 401)

    def test_analyze_url_missing_param(self):
        resp = self.client.post(
            '/api/seo/analyze',
            headers=self.auth_headers,
            json={'url': ''}
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertFalse(data['success'])

    def test_analyze_project_endpoint(self):
        resp = self.client.post(
            '/api/seo/analyze_project',
            headers=self.auth_headers,
            json={'project_path': 'tests/fixtures/seo/excellent.html', 'use_llm': False}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIn('report', data)
        self.assertGreaterEqual(data['report']['overall_score'], 85.0)

    def test_export_report_endpoint(self):
        sample_report = {
            'target': 'https://example.com',
            'overall_score': 88.0,
            'tier': 'Strong',
            'word_count': 450,
            'html_title': 'Example Tech Hub',
            'category_scores': {
                'Technical SEO': {'score': 90.0, 'weight': 0.2, 'passed_count': 3, 'warning_count': 0, 'critical_count': 0}
            },
            'findings': [],
            'action_plan': [],
            'ai_recommendations': 'Sample insights.'
        }

        resp = self.client.post(
            '/api/seo/export',
            headers=self.auth_headers,
            json={'report': sample_report}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIn('J.A.R.V.I.S. SEO Intelligence Report', data['markdown'])


if __name__ == "__main__":
    unittest.main()
