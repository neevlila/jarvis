"""
Integration tests for J.A.R.V.I.S. Security Assessment Engine REST API.
Verifies endpoints, authentication, scope validation, scan lifecycle,
findings update, remediation tracking, reporting, and AI explanation.
"""

import json
import unittest
import buddy
from security_engine.models import (
    Asset, AssetType, Finding, Severity, Confidence,
    ScanJob, ScanProfile, ScanStatus,
)
from security_engine.api import _store, _orchestrator


class TestSecurityAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        buddy.app.config['TESTING'] = True
        cls.client = buddy.app.test_client()
        cls.auth_headers = {
            'Content-Type': 'application/json',
            'X-JARVIS-Auth': buddy.api_token,
        }

    def test_unauthorized_without_token(self):
        resp = self.client.get('/api/v1/security/overview')
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertIn('Unauthorized', data.get('error', ''))

    def test_get_overview(self):
        resp = self.client.get('/api/v1/security/overview', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIn('overview', data)
        self.assertIn('assets_total', data['overview'])

    def test_list_scanners(self):
        resp = self.client.get('/api/v1/security/scanners', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        scanner_names = [s['name'] for s in data['scanners']]
        self.assertIn('nmap', scanner_names)
        self.assertIn('osv', scanner_names)

    def test_list_profiles(self):
        resp = self.client.get('/api/v1/security/profiles', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['profiles']), 4)

    def test_create_scope_requires_acknowledgment(self):
        resp = self.client.post(
            '/api/v1/security/scopes',
            headers=self.auth_headers,
            json={'target': 'example.com', 'profile': 'dependency_audit'}
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertFalse(data['success'])
        self.assertIn('authorization_acknowledged', data['error'])

    def test_create_scope_success(self):
        resp = self.client.post(
            '/api/v1/security/scopes',
            headers=self.auth_headers,
            json={
                'target': 'example.com',
                'profile': 'dependency_audit',
                'authorization_acknowledged': True,
                'owner': 'admin'
            }
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIn('id', data['scope'])

    def test_submit_scan_unauthorized_target(self):
        # Target with forbidden character
        resp = self.client.post(
            '/api/v1/security/scans',
            headers=self.auth_headers,
            json={
                'target': 'example.com; rm -rf /',
                'profile': 'dependency_audit',
                'authorization_acknowledged': True
            }
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertFalse(data['success'])

    def test_submit_scan_valid_dependency_audit(self):
        resp = self.client.post(
            '/api/v1/security/scans',
            headers=self.auth_headers,
            json={
                'target': 'example.com',
                'profile': 'dependency_audit',
                'authorization_acknowledged': True,
                'packages': [
                    {'name': 'requests', 'version': '2.20.0', 'ecosystem': 'PyPI'}
                ]
            }
        )
        self.assertIn(resp.status_code, (202, 400))
        data = json.loads(resp.data)
        if resp.status_code == 202:
            self.assertTrue(data['success'])
            self.assertIn('id', data['job'])

    def test_findings_workflow(self):
        # Create a test finding directly in store to test API retrieval and patch
        finding = Finding(
            title="Vulnerable Demo Library",
            description="Buffer overflow in demo component",
            severity=Severity.HIGH,
            confidence=Confidence.CONFIRMED,
            scanner="osv",
            affected_component="libdemo@1.0.0"
        )
        _store.save_finding(finding)

        # GET findings
        resp = self.client.get('/api/v1/security/findings', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['total'], 1)

        # GET single finding
        resp = self.client.get(f'/api/v1/security/findings/{finding.id}', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['finding']['id'], finding.id)

        # PATCH finding to false positive
        resp = self.client.patch(
            f'/api/v1/security/findings/{finding.id}',
            headers=self.auth_headers,
            json={'false_positive': True, 'fp_justification': 'Compensating control in place.'}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['finding']['false_positive'])

        # AI analysis of finding
        resp = self.client.post(
            f'/api/v1/security/findings/{finding.id}/analyze',
            headers=self.auth_headers,
            json={'asset_criticality': 'high'}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIn('ai_analysis', data)
        self.assertIn('executive_summary', data['ai_analysis'])

        # Remediation flow
        resp = self.client.post(
            f'/api/v1/security/findings/{finding.id}/remediation',
            headers=self.auth_headers,
            json={'recommended_action': 'Upgrade to 1.0.1', 'assigned_owner': 'SecOps'}
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['remediation']['assigned_owner'], 'SecOps')

        # Patch remediation
        resp = self.client.patch(
            f'/api/v1/security/findings/{finding.id}/remediation',
            headers=self.auth_headers,
            json={'status': 'in_progress', 'note': 'PR #42 opened'}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['remediation']['status'], 'in_progress')

    def test_reports_generation(self):
        job = ScanJob(
            target="test.local",
            profile=ScanProfile.SERVICE_INVENTORY,
            status=ScanStatus.COMPLETED
        )
        _store.save_scan_job(job)

        # HTML report
        resp = self.client.get(f'/api/v1/security/reports/{job.id}/html', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"J.A.R.V.I.S. Security Assessment Report", resp.data)

        # CSV report
        resp = self.client.get(f'/api/v1/security/reports/{job.id}/csv', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Finding ID,Severity", resp.data)

        # Executive summary
        resp = self.client.get(f'/api/v1/security/scans/{job.id}/executive_summary', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIn('executive_summary', data)
