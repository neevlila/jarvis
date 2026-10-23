"""
J.A.R.V.I.S. Security Assessment Engine — Flask API Blueprint
=============================================================
Registers all /api/v1/security/* routes.

Integrate into buddy.py with:
    from security_engine.api import security_bp, init_security_engine
    init_security_engine(app)
    app.register_blueprint(security_bp)

Authorization model
-------------------
All routes protected by the existing JARVIS CSRF token (checked in
buddy.py's before_request hook for /api/* paths).

Scope management
----------------
For this initial release, the API creates a temporary scope from the
request payload.  A full multi-user scope database is the next step.
An explicit 'authorization_acknowledged' flag in every scan request is
required — the server rejects any scan request that omits it.
"""

from __future__ import annotations

import json
import logging
import time
import os

from flask import Blueprint, jsonify, request, Response

from .models import (
    AuthorizedScope, ScanProfile, ScanStatus,
    Finding, Severity, VerificationStatus, RemediationRecord, RemediationStatus,
)
from .store import SecurityStore
from .scanner_base import ScannerRegistry
from .orchestrator import SecurityOrchestrator
from .reporting import ReportGenerator

logger = logging.getLogger("jarvis.security.api")

security_bp = Blueprint("security", __name__, url_prefix="/api/v1/security")

# Module-level singletons (initialised by init_security_engine)
_store:          SecurityStore | None      = None
_registry:       ScannerRegistry | None    = None
_orchestrator:   SecurityOrchestrator | None = None
_reporter:       ReportGenerator | None    = None


def init_security_engine(app) -> None:
    """
    Call once after creating the Flask app to wire up the security engine.
    Registers all scanner adapters and creates the singletons.
    """
    global _store, _registry, _orchestrator, _reporter

    data_dir = os.environ.get(
        "JARVIS_SECURITY_DATA_DIR",
        os.path.join(os.path.dirname(__file__), "..", "jarvis_security_data")
    )
    _store = SecurityStore(data_dir=data_dir)

    _registry = ScannerRegistry()

    # Register scanners — each checks its own availability
    try:
        from scanners.nmap_adapter import NmapScanner
        _registry.register(NmapScanner())
    except Exception as exc:
        logger.warning("Nmap adapter not loaded: %s", exc)

    try:
        from scanners.osv_adapter import OSVScanner
        _registry.register(OSVScanner())
    except Exception as exc:
        logger.warning("OSV adapter not loaded: %s", exc)

    try:
        from scanners.zap_adapter import ZAPScanner
        _registry.register(ZAPScanner())
    except Exception as exc:
        logger.warning("ZAP adapter not loaded: %s", exc)

    try:
        from scanners.greenbone_adapter import GreenboneScanner
        _registry.register(GreenboneScanner())
    except Exception as exc:
        logger.warning("Greenbone adapter not loaded: %s", exc)

    _orchestrator = SecurityOrchestrator(_store, _registry)
    _reporter     = ReportGenerator(_store)

    app.register_blueprint(security_bp)
    logger.info("Security Assessment Engine initialised.")


# ── Helper ────────────────────────────────────────────────────────────────────

def _require_engine():
    if not _store or not _orchestrator:
        return jsonify({"success": False, "error": "Security engine not initialised."}), 503
    return None


def _build_temp_scope(data: dict) -> tuple[AuthorizedScope | None, str | None]:
    """
    Build a temporary AuthorizedScope from request data.
    Requires 'authorization_acknowledged': true in the payload.
    """
    if not data.get("authorization_acknowledged"):
        return None, (
            "You must set 'authorization_acknowledged': true to confirm you "
            "own or have explicit written permission to scan the target."
        )

    targets = data.get("targets") or []
    if isinstance(targets, str):
        targets = [targets]
    target = data.get("target", "").strip()
    if target and target not in targets:
        targets.append(target)
    if not targets:
        return None, "At least one target is required."

    try:
        profile_str = data.get("profile", "dependency_audit")
        profiles = [ScanProfile(profile_str)]
    except ValueError:
        return None, f"Unknown profile '{data.get('profile')}'."

    scope = AuthorizedScope(
        targets=targets,
        profiles_allowed=profiles,
        owner=data.get("owner", "api_user"),
        notes=data.get("scope_notes", "Temporary scope created via API."),
        expires_at=time.time() + 3600,  # 1-hour expiry
    )
    # Persist so it can be referenced by job
    if _store:
        _store.save_scope(scope)
    return scope, None


# ── Routes ────────────────────────────────────────────────────────────────────

# --- Overview ---

@security_bp.route("/overview", methods=["GET"])
def security_overview():
    err = _require_engine()
    if err:
        return err
    return jsonify({"success": True, "overview": _orchestrator.overview()})


# --- Scanner health ---

@security_bp.route("/scanners", methods=["GET"])
def list_scanners():
    err = _require_engine()
    if err:
        return err
    health = _registry.health_all()
    return jsonify({"success": True, "scanners": health})


# --- Assets ---

@security_bp.route("/assets", methods=["GET"])
def list_assets():
    err = _require_engine()
    if err:
        return err
    page  = max(1, int(request.args.get("page", 1)))
    limit = min(200, max(1, int(request.args.get("limit", 50))))
    all_assets = _store.list_assets()
    total = len(all_assets)
    start = (page - 1) * limit
    page_assets = all_assets[start: start + limit]
    return jsonify({
        "success": True,
        "assets":  [a.to_dict() for a in page_assets],
        "total":   total,
        "page":    page,
        "limit":   limit,
    })


@security_bp.route("/assets/<asset_id>", methods=["GET"])
def get_asset(asset_id: str):
    err = _require_engine()
    if err:
        return err
    asset = _store.get_asset(asset_id)
    if not asset:
        return jsonify({"success": False, "error": "Asset not found."}), 404
    findings = _store.list_findings(asset_id=asset_id, limit=100)
    return jsonify({
        "success":  True,
        "asset":    asset.to_dict(),
        "findings": [f.to_dict(asset.criticality) for f in findings],
    })


# --- Scopes ---

@security_bp.route("/scopes", methods=["GET", "POST"])
def scopes():
    err = _require_engine()
    if err:
        return err

    if request.method == "GET":
        all_scopes = _store.list_scopes()
        return jsonify({"success": True, "scopes": [s.to_dict() for s in all_scopes]})

    data = request.get_json(force=True) or {}
    scope, error = _build_temp_scope(data)
    if error:
        return jsonify({"success": False, "error": error}), 400
    return jsonify({"success": True, "scope": scope.to_dict()}), 201


# --- Scan jobs ---

@security_bp.route("/scans", methods=["GET", "POST"])
def scans():
    err = _require_engine()
    if err:
        return err

    if request.method == "GET":
        limit = min(100, max(1, int(request.args.get("limit", 20))))
        status_str = request.args.get("status")
        status = None
        if status_str:
            try:
                status = ScanStatus(status_str)
            except ValueError:
                return jsonify({"success": False, "error": f"Unknown status '{status_str}'."}), 400
        jobs = _store.list_scan_jobs(status=status, limit=limit)
        return jsonify({"success": True, "scans": [j.to_dict() for j in jobs]})

    # POST — submit a scan
    data = request.get_json(force=True) or {}

    scope, error = _build_temp_scope(data)
    if error:
        return jsonify({"success": False, "error": error}), 400

    try:
        profile = ScanProfile(data.get("profile", "dependency_audit"))
    except ValueError:
        return jsonify({"success": False, "error": f"Unknown profile '{data.get('profile')}'."}), 400

    target = data.get("target", "").strip()
    if not target:
        return jsonify({"success": False, "error": "target is required."}), 400

    job, err_msg = _orchestrator.submit_scan(
        target=target,
        profile=profile,
        scope=scope,
        initiated_by=data.get("initiated_by", "api_user"),
        from_cloud=True,
        timeout_s=int(data.get("timeout_s", 300)),
        project_path=data.get("project_path"),
        packages=data.get("packages"),
    )

    if err_msg:
        return jsonify({"success": False, "error": err_msg, "job": job.to_dict()}), 400

    return jsonify({"success": True, "job": job.to_dict()}), 202


@security_bp.route("/scans/<job_id>", methods=["GET"])
def get_scan(job_id: str):
    err = _require_engine()
    if err:
        return err
    job = _store.get_scan_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "Scan job not found."}), 404
    findings = _store.list_findings(scan_job_id=job_id)
    return jsonify({
        "success":  True,
        "job":      job.to_dict(),
        "findings": [f.to_dict() for f in findings],
    })


@security_bp.route("/scans/<job_id>/executive_summary", methods=["GET"])
def scan_executive_summary(job_id: str):
    err = _require_engine()
    if err:
        return err
    job = _store.get_scan_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "Scan job not found."}), 404
    findings = _store.list_findings(scan_job_id=job_id)
    from .ai_analyst import AISecurityAnalyst
    summary = AISecurityAnalyst.generate_executive_summary(job, findings)
    return jsonify({"success": True, "executive_summary": summary})


@security_bp.route("/scans/<job_id>/cancel", methods=["POST"])
def cancel_scan(job_id: str):
    err = _require_engine()
    if err:
        return err
    ok, msg = _orchestrator.cancel_scan(job_id)
    status = 200 if ok else 400
    return jsonify({"success": ok, "message": msg}), status


# --- Findings ---

@security_bp.route("/findings", methods=["GET"])
def list_findings():
    err = _require_engine()
    if err:
        return err
    sev_str = request.args.get("severity")
    severity = None
    if sev_str:
        try:
            severity = Severity(sev_str)
        except ValueError:
            return jsonify({"success": False, "error": f"Unknown severity '{sev_str}'."}), 400
    asset_id    = request.args.get("asset_id")
    scan_job_id = request.args.get("scan_job_id")
    include_fp  = request.args.get("include_false_positives", "false").lower() == "true"
    limit       = min(500, max(1, int(request.args.get("limit", 100))))
    findings = _store.list_findings(
        asset_id=asset_id,
        scan_job_id=scan_job_id,
        severity=severity,
        include_false_positives=include_fp,
        limit=limit,
    )
    return jsonify({"success": True, "findings": [f.to_dict() for f in findings], "total": len(findings)})


@security_bp.route("/findings/<finding_id>", methods=["GET"])
def get_finding(finding_id: str):
    err = _require_engine()
    if err:
        return err
    finding = _store.get_finding(finding_id)
    if not finding:
        return jsonify({"success": False, "error": "Finding not found."}), 404
    rem = _store.get_remediation_for_finding(finding_id)
    return jsonify({
        "success":     True,
        "finding":     finding.to_dict(),
        "remediation": rem.to_dict() if rem else None,
    })


@security_bp.route("/findings/<finding_id>", methods=["PATCH"])
def update_finding(finding_id: str):
    """Mark as false positive or update verification status."""
    err = _require_engine()
    if err:
        return err
    finding = _store.get_finding(finding_id)
    if not finding:
        return jsonify({"success": False, "error": "Finding not found."}), 404
    data = request.get_json(force=True) or {}
    if "false_positive" in data:
        finding.false_positive   = bool(data["false_positive"])
        finding.fp_justification = data.get("fp_justification", "")
    if "verification" in data:
        try:
            finding.verification = VerificationStatus(data["verification"])
        except ValueError:
            return jsonify({"success": False, "error": "Invalid verification status."}), 400
    _store.save_finding(finding)
    return jsonify({"success": True, "finding": finding.to_dict()})


@security_bp.route("/findings/<finding_id>/analyze", methods=["POST"])
def analyze_finding_with_ai(finding_id: str):
    """Generate source-grounded AI explanation and prioritized actions for a finding."""
    err = _require_engine()
    if err:
        return err
    finding = _store.get_finding(finding_id)
    if not finding:
        return jsonify({"success": False, "error": "Finding not found."}), 404
    data = request.get_json(force=True) or {}
    asset_criticality = data.get("asset_criticality", "medium")
    from .ai_analyst import AISecurityAnalyst
    analysis = AISecurityAnalyst.explain_finding(finding, asset_criticality=asset_criticality)
    return jsonify({"success": True, "ai_analysis": analysis})


# --- Remediation ---

@security_bp.route("/findings/<finding_id>/remediation", methods=["GET", "POST", "PATCH"])
def remediation(finding_id: str):
    err = _require_engine()
    if err:
        return err
    finding = _store.get_finding(finding_id)
    if not finding:
        return jsonify({"success": False, "error": "Finding not found."}), 404

    if request.method == "GET":
        rec = _store.get_remediation_for_finding(finding_id)
        if not rec:
            return jsonify({"success": False, "error": "No remediation record yet."}), 404
        return jsonify({"success": True, "remediation": rec.to_dict()})

    data = request.get_json(force=True) or {}

    if request.method == "POST":
        rec = RemediationRecord(
            finding_id=finding_id,
            recommended_action=data.get("recommended_action", finding.remediation),
            assigned_owner=data.get("assigned_owner", ""),
            notes=[data.get("note", "")] if data.get("note") else [],
        )
        _store.save_remediation(rec)
        return jsonify({"success": True, "remediation": rec.to_dict()}), 201

    if request.method == "PATCH":
        rec = _store.get_remediation_for_finding(finding_id)
        if not rec:
            return jsonify({"success": False, "error": "No remediation record found."}), 404
        if "status" in data:
            try:
                rec.status = RemediationStatus(data["status"])
            except ValueError:
                return jsonify({"success": False, "error": "Invalid remediation status."}), 400
            if rec.status == RemediationStatus.RESOLVED:
                rec.closed_at = time.time()
        if "note" in data:
            rec.notes.append(f"[{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}] {data['note']}")
        if "assigned_owner" in data:
            rec.assigned_owner = data["assigned_owner"]
        _store.save_remediation(rec)
        return jsonify({"success": True, "remediation": rec.to_dict()})


# --- Reports ---

@security_bp.route("/reports/<job_id>/html", methods=["GET"])
def report_html(job_id: str):
    err = _require_engine()
    if err:
        return err
    html_content = _reporter.html_report(job_id)
    return Response(html_content, mimetype="text/html")


@security_bp.route("/reports/<job_id>/csv", methods=["GET"])
def report_csv(job_id: str):
    err = _require_engine()
    if err:
        return err
    csv_content = _reporter.csv_report(job_id)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=jarvis_security_{job_id[:8]}.csv"}
    )


# --- Scanner profiles reference ---

@security_bp.route("/profiles", methods=["GET"])
def list_profiles():
    profiles = [
        {
            "id":          "asset_discovery",
            "name":        "Asset Discovery",
            "description": "Host discovery on authorized networks. Identifies live hosts without port scanning.",
            "requires_agent": True,
            "scanners":    ["nmap"],
        },
        {
            "id":          "service_inventory",
            "name":        "Service Inventory",
            "description": "Controlled port and service detection on authorized hosts.",
            "requires_agent": True,
            "scanners":    ["nmap"],
        },
        {
            "id":          "web_baseline",
            "name":        "Web Baseline",
            "description": "Passive and baseline web security checks for authorized web applications.",
            "requires_agent": False,
            "scanners":    ["zap"],
        },
        {
            "id":          "dependency_audit",
            "name":        "Dependency Audit",
            "description": "Known-vulnerability checks for supplied project dependencies.",
            "requires_agent": False,
            "scanners":    ["osv"],
        },
        {
            "id":          "infrastructure_assessment",
            "name":        "Infrastructure Assessment",
            "description": "Approved infrastructure checks using configured vulnerability scanner.",
            "requires_agent": True,
            "scanners":    ["nmap", "greenbone"],
        },
        {
            "id":          "comprehensive",
            "name":        "Comprehensive Authorized Assessment",
            "description": "Bounded combination of all supported checks. Requires local agent.",
            "requires_agent": True,
            "scanners":    ["nmap", "greenbone"],
        },
    ]
    return jsonify({"success": True, "profiles": profiles})
