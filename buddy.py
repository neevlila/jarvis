import io
import json
import sys
import base64
import shutil
import tempfile
import uuid
import urllib.parse
import urllib.request
import logging
from bs4 import BeautifulSoup
logger = logging.getLogger(__name__)
import pyttsx3
import speech_recognition as sr
import pythoncom
import webbrowser
import os
import psutil
import platform
import subprocess
import pyautogui
import wikipedia
import time
import threading
from pynput.keyboard import Controller
import requests
import speedtest
import cv2
import re
import datetime
from queue import Queue
import win32gui
import win32con
import win32process
import winreg
import qrcode
import google.generativeai as genai
import config as cfg
import ppt_generator
import code_assistant
import email_writer
from wifi_helper import get_wifi_password, get_current_wifi
from llm_service import LLMService
from providers.provider_manager import ProviderManager
from desktop_engine import (
    ObservationEngine,
    PerceptionEngine,
    ContextEngine,
    DecisionEngine,
    ValidationEngine,
    ActionExecutor,
    VerificationEngine,
    DesktopOrchestrator,
    CoordinateSpace,
    Point,
    BoundingBox,
    CoordinateConverter
)
from idea_engine import (
    IdeaEngine,
    IdeaGenerationRequest,
    GenerationMode,
    StackAnalysis,
    ProjectIdea,
    MasterPromptConfig,
    VisualDirection,
    MotionLevel,
    ThreeDIntensity,
    TargetPlatform
)
from intelligence import (
    IntelligenceCoordinator,
    MemoryType,
    RiskLevel
)
from seo_engine import SEOEngine, SEOAuditReport
from geolocation_engine import (
    GeolocationService,
    GeolocationSynthesizer,
    IPIntentDetector,
    IPValidator,
    default_geolocation_service
)
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import logging

app = Flask(__name__, static_folder='web', static_url_path='')

# ── CORS: support localhost dev + Render production domain ────────────────────
import os as _os
_render_url = _os.environ.get("RENDER_EXTERNAL_URL", "")
_allowed_origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5001",
    "http://127.0.0.1:5001",
]
if _render_url:
    _allowed_origins.append(_render_url)
    _allowed_origins.append(_render_url.replace("http://", "https://"))
CORS(app, origins=_allowed_origins, supports_credentials=True)

# Disable Flask startup logs to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

import secrets
# Cryptographically secure random session token for CSRF protection
api_token = secrets.token_hex(16)

@app.before_request
def verify_security_token():
    # Exclude index page serving, CORS preflight pre-checks, favicon, and static assets
    if request.method == 'OPTIONS':
        return
    if request.path in ['/', '/index.html', '/favicon.ico', '/favicon.svg'] or request.path.startswith('/static/'):
        return
    
    # Verify samesite Strict cookie
    token = request.cookies.get('jarvis_token')
    if not token or token != api_token:
        # Fallback to header authorization
        header_token = request.headers.get('X-JARVIS-Auth')
        if header_token == api_token:
            return
        return jsonify({'error': 'Unauthorized: Access Denied. Invalid or missing security token.'}), 401

# Real-time interactive subprocess console globals
active_process = None
active_process_lock = threading.Lock()
output_queue = Queue()

def enqueue_output_chars(stream, stream_type):
    """Reads characters from a stream and pushes them to the shared output queue."""
    try:
        while True:
            char = stream.read(1)
            if not char:
                break
            output_queue.put((stream_type, char))
    except Exception:
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass

assistant_ref = None
thread_local = threading.local()

# ── CPU background sampler ─────────────────────────────────────────────
# psutil.cpu_percent(interval=None) returns 0.0 on first call and gives only
# the delta since the LAST call. Running it with interval=1 inside a daemon
# thread gives us an accurate, 1-second-averaged reading without blocking Flask.
_cpu_cached = 0.0

def _cpu_sampler_loop():
    global _cpu_cached
    while True:
        _cpu_cached = psutil.cpu_percent(interval=1.5)

_cpu_thread = threading.Thread(target=_cpu_sampler_loop, daemon=True)
_cpu_thread.start()
# ─────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    resp = app.send_static_file('index.html')
    resp.set_cookie('jarvis_token', api_token, httponly=True, samesite='Strict')
    return resp

@app.route('/favicon.ico')
@app.route('/favicon.svg')
def favicon():
    return app.send_static_file('favicon.svg')

@app.route('/api/status')
def get_status():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    try:
        cpu = round(_cpu_cached, 1)
        ram = psutil.virtual_memory().percent
        
        drives = []
        for partition in psutil.disk_partitions():
            try:
                if partition.mountpoint:
                    usage = psutil.disk_usage(partition.mountpoint)
                    drives.append({
                        'device': partition.device.replace('\\', ''),
                        'percent': usage.percent
                    })
            except Exception:
                pass
            
        notifications = []
        if hasattr(assistant_ref, 'notifications'):
            notifications = list(assistant_ref.notifications)
            assistant_ref.notifications.clear()

        context_summary = {}
        if hasattr(assistant_ref, 'get_context_summary'):
            try:
                context_summary = assistant_ref.get_context_summary()
            except Exception:
                pass

        return jsonify({
            'cpu': cpu,
            'ram': ram,
            'drives': drives,
            'typing_active': assistant_ref.typing_active,
            'paused': assistant_ref.paused,
            'notifications': notifications,
            'context': context_summary
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context')
def get_context_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    try:
        ctx = assistant_ref.get_current_context()
        return jsonify({'success': True, 'context': ctx.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/task', methods=['POST'])
def run_desktop_task_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    data = request.get_json() or {}
    goal = data.get('goal', '').strip()
    if not goal:
        return jsonify({'error': 'No goal provided'}), 400
    try:
        summary = assistant_ref.run_desktop_task(goal)
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vision', methods=['POST'])
def run_vision_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    data = request.get_json() or {}
    image_input = data.get('image', 'active_window.png')
    prompt = data.get('prompt', 'What is in this image?')
    try:
        desc = ProviderManager.vision(image_input=image_input, prompt=prompt)
        return jsonify({'success': True, 'description': desc})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/idea_engine/generate', methods=['POST'])
def generate_ideas_api():
    if not assistant_ref or not hasattr(assistant_ref, 'idea_engine'):
        return jsonify({'success': False, 'error': 'Idea Engine not initialized'}), 503
    data = request.get_json() or {}
    try:
        mode_str = data.get('mode', 'stack_to_ideas')
        try:
            mode = GenerationMode(mode_str)
        except Exception:
            mode = GenerationMode.STACK_TO_IDEAS

        req = IdeaGenerationRequest(
            technologies=data.get('technologies', []),
            problem_statement=data.get('problem_statement'),
            mode=mode,
            experience_level=data.get('experience_level', 'Intermediate'),
            project_type=data.get('project_type', 'Portfolio Project'),
            time_available=data.get('time_available', '2 weeks'),
            budget=data.get('budget', 'Free'),
            goal=data.get('goal', 'Solve real-world problem'),
            domain=data.get('domain', 'Open-ended'),
            difficulty=data.get('difficulty', 'Medium'),
            number_of_ideas=int(data.get('number_of_ideas', 5)),
            existing_project_details=data.get('existing_project_details')
        )
        res = assistant_ref.idea_engine.generate_ideas(req)
        return jsonify(res.to_dict())
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/idea_engine/analyze_stack', methods=['POST'])
def analyze_stack_api():
    if not assistant_ref or not hasattr(assistant_ref, 'idea_engine'):
        return jsonify({'success': False, 'error': 'Idea Engine not initialized'}), 503
    data = request.get_json() or {}
    technologies = data.get('technologies', [])
    try:
        analysis = assistant_ref.idea_engine.analyze_stack(technologies)
        return jsonify({'success': True, 'stack_analysis': analysis.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/idea_engine/idea/<idea_id>', methods=['GET'])
def get_idea_details_api(idea_id):
    if not assistant_ref or not hasattr(assistant_ref, 'idea_engine'):
        return jsonify({'success': False, 'error': 'Idea Engine not initialized'}), 503
    idea = assistant_ref.idea_engine.get_idea_by_id(idea_id)
    if not idea:
        return jsonify({'success': False, 'error': 'Idea not found in session memory'}), 404
    return jsonify({'success': True, 'idea': idea.to_dict()})

@app.route('/api/idea_engine/generate_master_prompt', methods=['POST'])
def generate_master_prompt_api():
    if not assistant_ref or not hasattr(assistant_ref, 'idea_engine'):
        return jsonify({'success': False, 'error': 'Idea Engine not initialized'}), 503
    data = request.get_json() or {}
    idea_id = data.get('idea_id')
    raw_idea_dict = data.get('idea')
    
    target_idea = None
    if idea_id:
        target_idea = assistant_ref.idea_engine.get_idea_by_id(idea_id)
        
    if not target_idea and raw_idea_dict:
        try:
            # Reconstruct ProjectIdea from dictionary
            tech_usage = []
            for tu in raw_idea_dict.get('technology_usage', []):
                if isinstance(tu, dict):
                    tech_usage.append(TechnologyMapping(
                        technology=tu.get('technology', ''),
                        role=tu.get('role', ''),
                        justification=tu.get('justification', '')
                    ))
            
            target_idea = ProjectIdea(
                id=raw_idea_dict.get('id', idea_id or 'custom-idea'),
                title=raw_idea_dict.get('title', 'Project Idea'),
                one_line_pitch=raw_idea_dict.get('one_line_pitch', ''),
                problem=raw_idea_dict.get('problem', ''),
                target_users=raw_idea_dict.get('target_users', 'End users and engineers'),
                solution=raw_idea_dict.get('solution', ''),
                core_features=raw_idea_dict.get('core_features', []),
                technology_usage=tech_usage,
                architecture_summary=raw_idea_dict.get('architecture_summary', ''),
                difficulty=raw_idea_dict.get('difficulty', 'Medium'),
                estimated_time=raw_idea_dict.get('estimated_time', '2 weeks'),
                risks=raw_idea_dict.get('risks', []),
                future_expansion=raw_idea_dict.get('future_expansion', [])
            )
            assistant_ref.idea_engine._session_ideas[target_idea.id] = target_idea
        except Exception as parse_err:
            print(f"[MASTER_PROMPT] Error reconstructing idea from payload: {parse_err}")

    if not target_idea:
        return jsonify({'success': False, 'error': 'Project idea not found. Please provide valid idea_id or idea payload.'}), 400

    # Parse config options
    def _parse_enum(enum_cls, val_str, default_val):
        if not val_str:
            return default_val
        for member in enum_cls:
            if member.value.lower() == str(val_str).lower() or member.name.lower() == str(val_str).lower():
                return member
        return default_val

    vis_dir = _parse_enum(VisualDirection, data.get('visual_direction'), VisualDirection.AUTO)
    mot_lvl = _parse_enum(MotionLevel, data.get('motion_level'), MotionLevel.BALANCED)
    threed_lvl = _parse_enum(ThreeDIntensity, data.get('threed_intensity'), ThreeDIntensity.AUTO)
    plat = _parse_enum(TargetPlatform, data.get('target_platform'), TargetPlatform.UNIVERSAL)

    config = MasterPromptConfig(
        visual_direction=vis_dir,
        motion_level=mot_lvl,
        threed_intensity=threed_lvl,
        target_platform=plat,
        custom_visual_notes=data.get('custom_visual_notes'),
        project_scope=data.get('project_scope', 'Full-stack Production MVP'),
        technical_depth=data.get('technical_depth', 'High / Production-ready')
    )

    try:
        master_prompt = assistant_ref.idea_engine.generate_master_prompt(target_idea, config)
        return jsonify({'success': True, 'prompt': master_prompt.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/idea_engine/save_master_prompt', methods=['POST'])
def save_master_prompt_api():
    if not assistant_ref:
        return jsonify({'success': False, 'error': 'Assistant not initialized'}), 503
    data = request.get_json() or {}
    prompt_id = data.get('prompt_id')
    if not prompt_id:
        return jsonify({'success': False, 'error': 'prompt_id is required'}), 400

    prompt = assistant_ref.idea_engine.get_master_prompt(prompt_id)
    if not prompt:
        return jsonify({'success': False, 'error': 'Prompt not found in active session'}), 404

    # Save to durable memory if intelligence coordinator is available
    if hasattr(assistant_ref, 'intelligence') and assistant_ref.intelligence:
        assistant_ref.intelligence.memory_engine.store(
            content=f"Master Build Specification for '{prompt.project_title}' (Platform: {prompt.config.target_platform.value}): {prompt.full_markdown_prompt[:300]}...",
            mem_type=MemoryType.PROJECT,
            source="master_prompt_engine",
            confidence=1.0,
            tags=["master_prompt", "blueprint", "specification", prompt.project_title.lower()]
        )

    return jsonify({'success': True, 'saved': True, 'prompt_id': prompt_id})

@app.route('/api/idea_engine/master_prompt/<prompt_id>', methods=['GET'])
def get_master_prompt_api(prompt_id):
    if not assistant_ref or not hasattr(assistant_ref, 'idea_engine'):
        return jsonify({'success': False, 'error': 'Idea Engine not initialized'}), 503
    prompt = assistant_ref.idea_engine.get_master_prompt(prompt_id)
    if not prompt:
        return jsonify({'success': False, 'error': 'Prompt not found'}), 404
    return jsonify({'success': True, 'prompt': prompt.to_dict()})

# ─────────────────────────────────────────────────────────────────────────────
# J.A.R.V.I.S. SEO Intelligence REST Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/seo/analyze', methods=['POST'])
def seo_analyze_api():
    if not assistant_ref or not hasattr(assistant_ref, 'seo_engine'):
        return jsonify({'success': False, 'error': 'SEO Intelligence engine not initialized'}), 503
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'Website URL is required'}), 400
    target_keyword = data.get('target_keyword')
    use_llm = data.get('use_llm', True)
    try:
        report = assistant_ref.seo_engine.analyze_url(url, target_keyword=target_keyword, use_llm=use_llm)
        # Also store into memory via intelligence coordinator if available
        if hasattr(assistant_ref, 'intelligence') and report.overall_score > 0:
            try:
                assistant_ref.intelligence.memory_engine.store(
                    content=f"SEO Audit for '{report.target}': Score {report.overall_score:.1f}/100 ({report.tier.value}). {len(report.findings)} findings.",
                    mem_type=MemoryType.TASK,
                    source="seo_engine",
                    confidence=0.98,
                    tags=["seo", "url_audit", "website"]
                )
            except Exception:
                pass
        return jsonify({'success': True, 'report': report.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/seo/analyze_project', methods=['POST'])
def seo_analyze_project_api():
    if not assistant_ref or not hasattr(assistant_ref, 'seo_engine'):
        return jsonify({'success': False, 'error': 'SEO Intelligence engine not initialized'}), 503
    data = request.get_json() or {}
    project_path = data.get('project_path', '.')
    target_keyword = data.get('target_keyword')
    use_llm = data.get('use_llm', True)
    try:
        report = assistant_ref.seo_engine.analyze_project(project_path, target_keyword=target_keyword, use_llm=use_llm)
        if hasattr(assistant_ref, 'intelligence') and report.overall_score > 0:
            try:
                assistant_ref.intelligence.memory_engine.store(
                    content=f"Local Template SEO Audit for '{report.target}': Score {report.overall_score:.1f}/100 ({report.tier.value}).",
                    mem_type=MemoryType.PROJECT,
                    source="seo_engine",
                    confidence=0.98,
                    tags=["seo", "project_audit", "template"]
                )
            except Exception:
                pass
        return jsonify({'success': True, 'report': report.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/seo/export', methods=['POST'])
def seo_export_api():
    data = request.get_json() or {}
    report_dict = data.get('report')
    if not report_dict:
        return jsonify({'success': False, 'error': 'Report payload is required'}), 400
    try:
        from seo_engine.models import SEOAuditReport, ScoreTier, CategoryScore, SEOFinding, SEOActionItem, PerformanceSignalsData
        # Reconstruct report object for markdown exporter
        cat_scores = {}
        for k, v in report_dict.get('category_scores', {}).items():
            cat_scores[k] = CategoryScore(
                category=v.get('category', k),
                score=v.get('score', 0.0),
                weight=v.get('weight', 0.1),
                passed_count=v.get('passed_count', 0),
                warning_count=v.get('warning_count', 0),
                critical_count=v.get('critical_count', 0),
                checks_summary=v.get('checks_summary', [])
            )
        
        findings = []
        for f in report_dict.get('findings', []):
            findings.append(SEOFinding(
                id=f.get('id', ''),
                category=f.get('category', ''),
                severity=f.get('severity', 'MEDIUM'),
                title=f.get('title', ''),
                problem=f.get('problem', ''),
                evidence=f.get('evidence', ''),
                evidence_type=f.get('evidence_type', 'OBSERVED'),
                recommendation=f.get('recommendation', ''),
                impact=f.get('impact', 'Medium'),
                effort=f.get('effort', 'Low'),
                confidence=f.get('confidence', 1.0),
                why_it_matters=f.get('why_it_matters', '')
            ))
            
        action_plan = []
        for a in report_dict.get('action_plan', []):
            action_plan.append(SEOActionItem(
                rank=a.get('rank', 1),
                title=a.get('title', ''),
                action=a.get('action', ''),
                impact=a.get('impact', 'High'),
                effort=a.get('effort', 'Low'),
                category=a.get('category', 'Technical'),
                why_it_matters=a.get('why_it_matters', '')
            ))

        report_obj = SEOAuditReport(
            id=report_dict.get('id', ''),
            target=report_dict.get('target', ''),
            mode=report_dict.get('mode', 'url'),
            target_keyword=report_dict.get('target_keyword'),
            overall_score=report_dict.get('overall_score', 0.0),
            tier=ScoreTier(report_dict.get('tier', 'Moderate')) if report_dict.get('tier') in [t.value for t in ScoreTier] else ScoreTier.MODERATE,
            summary=report_dict.get('summary', ''),
            category_scores=cat_scores,
            findings=findings,
            action_plan=action_plan,
            ai_recommendations=report_dict.get('ai_recommendations'),
            html_title=report_dict.get('html_title', ''),
            meta_description=report_dict.get('meta_description', ''),
            canonical_url=report_dict.get('canonical_url'),
            h1_headings=report_dict.get('h1_headings', []),
            word_count=report_dict.get('word_count', 0),
            status_code=report_dict.get('status_code', 200),
            timestamp=report_dict.get('timestamp', time.time()),
            disclaimer=report_dict.get('disclaimer', '')
        )

        md = SEOEngine.export_report_markdown(report_obj)
        return jsonify({'success': True, 'markdown': md})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# J.A.R.V.I.S. Intelligence REST Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/intelligence/analyze_project', methods=['POST'])
def analyze_project_api():
    if not assistant_ref or not hasattr(assistant_ref, 'intelligence'):
        return jsonify({'success': False, 'error': 'Intelligence subsystem not initialized'}), 503
    data = request.get_json() or {}
    project_path = data.get('project_path', '.')
    try:
        report = assistant_ref.intelligence.analyze_project(project_path)
        return jsonify({'success': True, 'report': report.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intelligence/decompose_goal', methods=['POST'])
def decompose_goal_api():
    if not assistant_ref or not hasattr(assistant_ref, 'intelligence'):
        return jsonify({'success': False, 'error': 'Intelligence subsystem not initialized'}), 503
    data = request.get_json() or {}
    goal = data.get('goal', '')
    if not goal:
        return jsonify({'success': False, 'error': 'Goal description is required'}), 400
    use_llm = data.get('use_llm', True)
    try:
        plan = assistant_ref.intelligence.decompose_goal(goal, context_data=data.get('context'), use_llm=use_llm)
        return jsonify({'success': True, 'plan': plan.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intelligence/critique', methods=['POST'])
def critique_api():
    if not assistant_ref or not hasattr(assistant_ref, 'intelligence'):
        return jsonify({'success': False, 'error': 'Intelligence subsystem not initialized'}), 503
    data = request.get_json() or {}
    content = data.get('content', '')
    user_goal = data.get('user_goal')
    use_llm = data.get('use_llm', False)
    try:
        critique = assistant_ref.intelligence.critique_candidate(
            candidate_content=content,
            user_goal=user_goal,
            context_data=data.get('context'),
            use_llm=use_llm
        )
        return jsonify({'success': True, 'critique': critique.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intelligence/memory', methods=['GET', 'POST', 'DELETE'])
def memory_api():
    if not assistant_ref or not hasattr(assistant_ref, 'intelligence'):
        return jsonify({'success': False, 'error': 'Intelligence subsystem not initialized'}), 503
    
    mem_engine = assistant_ref.intelligence.memory_engine

    if request.method == 'GET':
        query = request.args.get('query', '')
        type_filter_str = request.args.get('type')
        type_filter = None
        if type_filter_str:
            try:
                type_filter = MemoryType(type_filter_str)
            except Exception:
                pass
        
        if query:
            entries = mem_engine.retrieve(query=query, type_filter=type_filter, limit=15)
        else:
            entries = mem_engine.get_all(type_filter=type_filter)
        return jsonify({'success': True, 'entries': [e.to_dict() for e in entries]})

    elif request.method == 'POST':
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'success': False, 'error': 'Memory content is required'}), 400
        
        type_str = data.get('type', 'semantic')
        try:
            mtype = MemoryType(type_str)
        except Exception:
            mtype = MemoryType.SEMANTIC

        entry = mem_engine.store(
            content=content,
            mem_type=mtype,
            source=data.get('source', 'user_web_api'),
            confidence=float(data.get('confidence', 0.95)),
            tags=data.get('tags', []),
            verified=bool(data.get('verified', True))
        )
        return jsonify({'success': True, 'entry': entry.to_dict()})

    elif request.method == 'DELETE':
        entry_id = request.args.get('id')
        if not entry_id:
            return jsonify({'success': False, 'error': 'Entry ID is required'}), 400
        deleted = mem_engine.delete(entry_id)
        return jsonify({'success': deleted})

@app.route('/api/intelligence/skills', methods=['GET'])
def list_skills_api():
    if not assistant_ref or not hasattr(assistant_ref, 'intelligence'):
        return jsonify({'success': False, 'error': 'Intelligence subsystem not initialized'}), 503
    skills_meta = assistant_ref.intelligence.skill_registry.list_skills()
    return jsonify({'success': True, 'skills': [s.to_dict() for s in skills_meta]})

@app.route('/api/intelligence/performance', methods=['GET'])
def get_performance_api():
    if not assistant_ref or not hasattr(assistant_ref, 'intelligence'):
        return jsonify({'success': False, 'error': 'Intelligence subsystem not initialized'}), 503
    snapshot = assistant_ref.intelligence.get_performance_snapshot()
    return jsonify({'success': True, 'performance': snapshot.to_dict()})

@app.route('/api/intelligence/risk_assess', methods=['POST'])
def risk_assess_api():
    if not assistant_ref or not hasattr(assistant_ref, 'intelligence'):
        return jsonify({'success': False, 'error': 'Intelligence subsystem not initialized'}), 503
    data = request.get_json() or {}
    action_name = data.get('action', 'unknown')
    target = data.get('target')
    command_args = data.get('command_args')
    assessment = assistant_ref.intelligence.assess_risk(
        action_name=action_name,
        target=target,
        command_args=command_args,
        context=data.get('context')
    )
    return jsonify({'success': True, 'risk_assessment': assessment.to_dict()})

@app.route('/api/toggle_pause', methods=['POST'])
def toggle_pause():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    assistant_ref.paused = not assistant_ref.paused
    return jsonify({'success': True, 'paused': assistant_ref.paused})

@app.route('/api/diagnostics', methods=['POST'])
def run_diagnostics_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    thread_local.is_api_request = True
    try:
        report = assistant_ref.run_diagnostics()
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/geolocation/lookup', methods=['POST'])
def geolocation_lookup_api():
    data = request.get_json() or {}
    ip = data.get('ip', '').strip()
    if not ip:
        return jsonify({'error': 'No IP address provided.'}), 400
    try:
        service = getattr(assistant_ref, 'geolocation_service', default_geolocation_service) if assistant_ref else default_geolocation_service
        result = service.lookup(ip)
        return jsonify({
            'success': result.is_valid and result.has_coordinates,
            'result': result.to_dict(),
            'chat_response': GeolocationSynthesizer.build_chat_response(result),
            'context': GeolocationSynthesizer.build_context_assertions(result)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/command', methods=['POST'])
def run_command_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    data = request.get_json() or {}
    command = data.get('command', '').strip()
    if not command:
        return jsonify({'error': 'No command provided'}), 400
        
    assistant_ref.recent_responses = []
    assistant_ref.redirect_info = None
    assistant_ref.location_target = None
    
    thread_local.is_api_request = True
    try:
        should_exit = assistant_ref.process_command_with_mode(command, type_mode=True)
        response_text = " ".join(assistant_ref.recent_responses)
        if not response_text:
            response_text = "Command executed."
            
        redirect_data = getattr(assistant_ref, 'redirect_info', None)
        location_data = getattr(assistant_ref, 'location_target', None)
        if location_data:
            assistant_ref.location_target = None

        resp_payload = {
            'success': True,
            'response': response_text,
            'should_exit': should_exit
        }
        if location_data:
            resp_payload['location_target'] = location_data

        if redirect_data:
            assistant_ref.redirect_info = None
            resp_payload.update({
                'action': redirect_data.get('action'),
                'prompt': redirect_data.get('prompt'),
                'language': redirect_data.get('language'),
                'style': redirect_data.get('style'),
                'aspect_ratio': redirect_data.get('aspect_ratio')
            })
            
        return jsonify(resp_payload)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        thread_local.is_api_request = False

@app.route('/api/generate_qr', methods=['POST'])
def generate_qr_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
        
    try:
        img = qrcode.make(text)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"qr_{ts}.png"
        return jsonify({
            'success': True,
            'image': f"data:image/png;base64,{img_base64}",
            'filename': fname
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_qr', methods=['POST'])
def save_qr_api():
    data = request.get_json() or {}
    image_data = data.get('image', '').strip()
    filename = data.get('filename', '').strip()
    if not image_data or not filename:
        return jsonify({'error': 'Missing image or filename'}), 400
        
    # Security Hardening: Prevent directory traversal & restrict extensions
    filename = os.path.basename(filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg']:
        return jsonify({'error': 'Invalid file extension. Only PNG and JPG are permitted.'}), 400
        
    try:
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        img_bytes = base64.b64decode(image_data)
        with open(filename, 'wb') as f:
            f.write(img_bytes)
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/weather')
def get_weather_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    city = request.args.get('city', '').strip()
    if not city:
        return jsonify({'error': 'No city provided'}), 400
        
    try:
        api_key = cfg.WeatherConfig.WEATHER_API_KEY
        if not api_key:
            return jsonify({'error': 'Weather API key not configured in .env'}), 400
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f"Failed to fetch weather for {city}"}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/news')
def get_news_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    try:
        api_key = cfg.NewsConfig.NEWS_API_KEY
        if not api_key:
            return jsonify({'error': 'News API key not configured in .env'}), 400
            
        category = request.args.get('category', 'general').lower().strip()
        
        if category == 'ai':
            url = f"https://newsapi.org/v2/everything?q=Artificial%20Intelligence%20OR%20AI&language=en&sortBy=publishedAt&apiKey={api_key}"
        elif category == 'politics':
            url = f"https://newsapi.org/v2/everything?q=politics&language=en&sortBy=publishedAt&apiKey={api_key}"
        elif category in ['sports', 'technology', 'business']:
            url = f"https://newsapi.org/v2/top-headlines?country=us&category={category}&apiKey={api_key}"
        else:
            url = f"https://newsapi.org/v2/top-headlines?country=us&category=general&apiKey={api_key}"
            
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch news'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/news_summary', methods=['POST'])
def news_summary_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    try:
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        
        if not title:
            return jsonify({'error': 'No title provided'}), 400
            
        prompt = (
            f"Generate a concise, informative news summary of exactly 3 to 4 lines (about 60-80 words) for this article:\n"
            f"Title: {title}\n"
            f"Content: {content}\n\n"
            "Requirements:\n"
            "1. Must be exactly 3 to 4 lines/sentences long.\n"
            "2. Do not use any markdown formatting, asterisks, bolding, list tags, HTML, or JSON.\n"
            "3. Return only the plain text summary."
        )
        
        summary = ProviderManager.gemini(prompt)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/listen_voice', methods=['POST'])
def listen_voice_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    thread_local.is_api_request = True
    try:
        query = assistant_ref.listen_single_capture()
        if query == "none":
            return jsonify({'success': False, 'error': 'Could not recognize speech or listening timed out.'})
            
        assistant_ref.recent_responses = []
        should_exit = assistant_ref.process_command_with_mode(query, type_mode=True)
        response_text = " ".join(assistant_ref.recent_responses)
        if not response_text:
            response_text = "Command executed."
        return jsonify({
            'success': True,
            'query': query,
            'response': response_text,
            'should_exit': should_exit
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate_email', methods=['POST'])
def generate_email_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    try:
        data = request.get_json() or {}
        to_email = data.get('to', '').strip()
        role = data.get('role', '').strip()
        custom_role = data.get('custom_role', '').strip()
        about = data.get('about', '').strip()
        sender_name = data.get('sender_name', '').strip()
        sender_dept = data.get('sender_dept', '').strip()
        start_date = data.get('start_date', '').strip()
        end_date = data.get('end_date', '').strip()
        email_format = data.get('format', 'Formal').strip()
        
        recipient_role = custom_role if (role.lower() == 'custom' and custom_role) else role
        
        sender_details = {
            "sender_name": sender_name,
            "sender_dept": sender_dept,
            "start_date": start_date,
            "end_date": end_date
        }
        
        res = email_writer.generate_email_mistral(
            prompt_topic=f"Write an email about {about}",
            role=recipient_role,
            about=about,
            email_format=email_format,
            sender_details=sender_details
        )
        
        return jsonify({
            'success': True,
            'subject': res.get("subject", "Email Draft"),
            'body': res.get("body", "")
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate_ppt', methods=['POST'])
def generate_ppt_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    data = request.get_json() or {}
    topic = data.get('topic', '').strip()
    slide_count = data.get('slide_count', 6)
    theme_name = data.get('theme_name', 'cyberpunk')
    custom_titles = data.get('slide_titles', [])
    
    if not topic:
        return jsonify({'error': 'No topic provided'}), 400
        
    try:
        themes = {
            "cyberpunk": {
                "background_gradient": {"start": "#07090D", "end": "#0A1F30"},
                "text": {"primary": "#00D2FF", "secondary": "#8DA4B4"},
                "fonts": {"title": "Outfit", "body": "Outfit"},
                "accent": "#00FFCC"
            },
            "emerald": {
                "background_gradient": {"start": "#050B08", "end": "#0C1E14"},
                "text": {"primary": "#00FFCC", "secondary": "#94D2BD"},
                "fonts": {"title": "Outfit", "body": "Outfit"},
                "accent": "#0A9396"
            },
            "amber": {
                "background_gradient": {"start": "#0F0A05", "end": "#24170A"},
                "text": {"primary": "#FFB703", "secondary": "#E9D8A6"},
                "fonts": {"title": "Outfit", "body": "Outfit"},
                "accent": "#CA6702"
            },
            "violet": {
                "background_gradient": {"start": "#0B050F", "end": "#1D0C2E"},
                "text": {"primary": "#E0AAFF", "secondary": "#C77DFF"},
                "fonts": {"title": "Outfit", "body": "Outfit"},
                "accent": "#9D4EDD"
            },
            "crimson": {
                "background_gradient": {"start": "#0D0507", "end": "#240A10"},
                "text": {"primary": "#FF4D6D", "secondary": "#FFCCD5"},
                "fonts": {"title": "Outfit", "body": "Outfit"},
                "accent": "#C9184A"
            }
        }
        
        selected_theme = themes.get(theme_name, themes["cyberpunk"])
        
        if not custom_titles:
            custom_titles = ppt_generator._generate_outline_titles(topic, slide_count)
            
        path = ppt_generator.generate_ppt_custom(
            topic=topic,
            slide_count=slide_count,
            slide_titles=custom_titles,
            theme=selected_theme
        )
        
        return jsonify({
            'success': True,
            'path': path,
            'filename': os.path.basename(path)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/open_file', methods=['POST'])
def open_file_api():
    data = request.get_json() or {}
    path = data.get('path', '').strip()
    if not path:
        return jsonify({'error': 'Path not specified'}), 400
    
    # Enforce directory restriction to prevent arbitrary system execution
    abs_target = os.path.abspath(path)
    workspace_dir = os.path.abspath(os.path.dirname(__file__))
    if not abs_target.startswith(workspace_dir):
        return jsonify({'error': 'Access Denied: Path is outside the J.A.R.V.I.S. workspace.'}), 403
        
    if not os.path.exists(abs_target):
        return jsonify({'error': 'File not found'}), 404
    try:
        os.startfile(abs_target)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def extract_json_data(res_text):
    text_stripped = res_text.strip()
    try:
        return json.loads(text_stripped)
    except Exception:
        pass
    json_match = re.search(r'```json\s*(.*?)\s*```', res_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except Exception:
            pass
    brace_match = re.search(r'(\{.*\})', res_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1).strip())
        except Exception:
            pass
    return None

@app.route('/api/code_assistant', methods=['POST'])
def code_assistant_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    language = data.get('language', 'python').strip()
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
        
    try:
        res_text = code_assistant.generate_code_llama(prompt, language, is_api_call=True)
        
        parsed = extract_json_data(res_text)
        if parsed and isinstance(parsed, dict) and "code" in parsed:
            code = parsed["code"]
        else:
            code_match = re.search(r'```(?:[a-zA-Z0-9+#-]+)?\s*(.*?)\s*```', res_text, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                code = res_text
            
        # Ensure escaped newlines are properly expanded to multi-line code
        if isinstance(code, str):
            if "\\n" in code and "\n" not in code:
                code = code.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "    ").replace('\\"', '"').replace("\\'", "'")
            code = code.replace("\r\n", "\n").replace("\r", "\n")

        return jsonify({
            'success': True,
            'code': code,
            'language': language
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Subprocess management for live interactive code execution
active_process = None
active_process_lock = threading.Lock()
output_queue = Queue()
last_console_interaction = time.perf_counter()

def enqueue_output_chars(stream, stream_type):
    try:
        while True:
            char = stream.read(1)
            if not char:
                break
            output_queue.put((stream_type, char))
    except Exception:
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass

@app.route('/api/run_code', methods=['POST'])
def run_code_api():
    global active_process, output_queue, last_console_interaction
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    language = data.get('language', 'python').strip().lower()
    
    if not code:
        return jsonify({'success': False, 'error': 'No code provided'}), 400
        
    supported_langs = ['python', 'javascript', 'html', 'css', 'cpp', 'java', 'csharp', 'go', 'typescript', 'sql', 'rust']
    if language not in supported_langs:
        return jsonify({'success': False, 'error': f'Unsupported language: {language}'}), 400
        
    # Markup languages cannot be executed in console
    if language in ['html', 'css', 'sql']:
        msg = f"{language.upper()} cannot be executed directly in the terminal console. You can download and run this file locally."
        if language == 'sql':
            msg = "SQL requires a connected database instance to run queries. Please use your local database compiler."
        return jsonify({
            'success': True,
            'started': False,
            'stdout': msg,
            'stderr': '',
            'exit_code': 0,
            'duration': 0.0
        })

    # Prepare temp files directory in J.A.R.V.I.S workspace
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_run')
    os.makedirs(temp_dir, exist_ok=True)
    run_id = uuid.uuid4().hex
    
    run_cmd = None
    
    try:
        if language == 'python':
            filepath = os.path.join(temp_dir, f"run_{run_id}.py")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            run_cmd = ['python', '-u', filepath]
            
        elif language == 'javascript':
            if not shutil.which('node'):
                return jsonify({'success': False, 'error': 'Node.js is not installed or not on system PATH.'}), 400
            filepath = os.path.join(temp_dir, f"run_{run_id}.js")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            run_cmd = ['node', filepath]
            
        elif language == 'typescript':
            if not shutil.which('ts-node'):
                return jsonify({'success': False, 'error': 'ts-node is not installed or not on system PATH. Please run "npm install -g ts-node typescript" to execute TypeScript.'}), 400
            filepath = os.path.join(temp_dir, f"run_{run_id}.ts")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            run_cmd = ['ts-node', filepath]

        elif language == 'cpp':
            if not shutil.which('g++') and not shutil.which('clang++'):
                return jsonify({'success': False, 'error': 'G++ or Clang++ compiler not found on system PATH. Please install GCC/Clang to compile C++.'}), 400
            compiler = 'g++' if shutil.which('g++') else 'clang++'
            filepath = os.path.join(temp_dir, f"run_{run_id}.cpp")
            outpath = os.path.join(temp_dir, f"run_{run_id}.exe" if os.name == 'nt' else f"run_{run_id}")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            # Compile C++ synchronously
            compile_res = subprocess.run(
                [compiler, filepath, '-o', outpath],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir
            )
            if compile_res.returncode != 0:
                return jsonify({
                    'success': True,
                    'started': False,
                    'stdout': "",
                    'stderr': f"Compilation Error:\n{compile_res.stderr}",
                    'exit_code': compile_res.returncode,
                    'duration': 0.0
                })
            run_cmd = [outpath]
                
        elif language == 'go':
            if not shutil.which('go'):
                return jsonify({'success': False, 'error': 'Go compiler not found on system PATH. Please install Go to run Go code.'}), 400
            filepath = os.path.join(temp_dir, f"run_{run_id}.go")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            run_cmd = ['go', 'run', filepath]
            
        elif language == 'rust':
            if not shutil.which('rustc'):
                return jsonify({'success': False, 'error': 'Rust compiler (rustc) not found on system PATH. Please install Rust to run Rust code.'}), 400
            filepath = os.path.join(temp_dir, f"run_{run_id}.rs")
            outpath = os.path.join(temp_dir, f"run_{run_id}.exe" if os.name == 'nt' else f"run_{run_id}")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            # Compile Rust synchronously
            compile_res = subprocess.run(
                ['rustc', filepath, '--out-dir', temp_dir],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir
            )
            if compile_res.returncode != 0:
                return jsonify({
                    'success': True,
                    'started': False,
                    'stdout': "",
                    'stderr': f"Compilation Error:\n{compile_res.stderr}",
                    'exit_code': compile_res.returncode,
                    'duration': 0.0
                })
            run_cmd = [outpath]
                
        elif language == 'java':
            if not shutil.which('javac') or not shutil.which('java'):
                return jsonify({'success': False, 'error': 'JDK (javac/java) not found on system PATH. Please install JDK to run Java.'}), 400
            import re
            class_match = re.search(r'public\s+class\s+(\w+)', code)
            class_name = class_match.group(1) if class_match else f"Run_{run_id}"
            if not class_match:
                code = f"public class {class_name} {{\npublic static void main(String[] args) {{\n{code}\n}}\n}}"
            filepath = os.path.join(temp_dir, f"{class_name}.java")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            # Compile Java synchronously
            compile_res = subprocess.run(
                ['javac', filepath],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir
            )
            if compile_res.returncode != 0:
                return jsonify({
                    'success': True,
                    'started': False,
                    'stdout': "",
                    'stderr': f"Compilation Error:\n{compile_res.stderr}",
                    'exit_code': compile_res.returncode,
                    'duration': 0.0
                })
            run_cmd = ['java', class_name]
                
        elif language == 'csharp':
            if not shutil.which('dotnet') and not shutil.which('mcs'):
                return jsonify({'success': False, 'error': '.NET CLI (dotnet) or Mono compiler (mcs) not found. Please install .NET Core SDK to compile C#.'}), 400
            if shutil.which('mcs'):
                filepath = os.path.join(temp_dir, f"run_{run_id}.cs")
                outpath = os.path.join(temp_dir, f"run_{run_id}.exe")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code)
                # Compile C# synchronously
                compile_res = subprocess.run(
                    ['mcs', filepath, f'-out:{outpath}'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )
                if compile_res.returncode != 0:
                    return jsonify({
                        'success': True,
                        'started': False,
                        'stdout': "",
                        'stderr': f"Compilation Error:\n{compile_res.stderr}",
                        'exit_code': compile_res.returncode,
                        'duration': 0.0
                    })
                run_cmd = ['mono', outpath] if os.name != 'nt' else [outpath]
            else:
                return jsonify({'success': False, 'error': 'C# compilation requires Mono (mcs) in this environment.'}), 400

        # Terminate any active process
        with active_process_lock:
            if active_process and active_process.poll() is None:
                try:
                    active_process.terminate()
                    active_process.wait(timeout=1)
                except Exception:
                    try:
                        active_process.kill()
                    except Exception:
                        pass
            
            # Clear output queue
            while not output_queue.empty():
                try:
                    output_queue.get_nowait()
                except Exception:
                    break
            
            # Start process asynchronously with pipe support and unbuffered IO
            proc_env = os.environ.copy()
            proc_env["PYTHONUNBUFFERED"] = "1"
            proc_env["PYTHONIOENCODING"] = "utf-8"

            active_process = subprocess.Popen(
                run_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=proc_env,
                cwd=temp_dir
            )
            
        # Start daemon threads to read stdout/stderr character-by-character
        t_out = threading.Thread(target=enqueue_output_chars, args=(active_process.stdout, 'stdout'), daemon=True)
        t_err = threading.Thread(target=enqueue_output_chars, args=(active_process.stderr, 'stderr'), daemon=True)
        t_out.start()
        t_err.start()
        
        last_console_interaction = time.perf_counter()
        return jsonify({
            'success': True,
            'started': True
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f"Execution exception: {str(e)}"}), 500

@app.route('/api/console_stream')
def console_stream_api():
    def generate():
        global active_process, output_queue, last_console_interaction
        import queue
        stream_start_time = time.perf_counter()
        
        while True:
            # Check interactive safety timeout: allow 60.0s of inactivity
            now = time.perf_counter()
            idle_elapsed = now - last_console_interaction
            total_elapsed = now - stream_start_time
            if idle_elapsed > 60.0 and total_elapsed > 60.0:
                with active_process_lock:
                    if active_process and active_process.poll() is None:
                        try:
                            active_process.terminate()
                            active_process.wait(timeout=1)
                        except Exception:
                            try:
                                active_process.kill()
                            except Exception:
                                pass
                        yield f"data: {json.dumps({'type': 'stderr', 'text': '\\n[Process terminated: Inactive for 60 seconds.]'})}\n\n"
                        yield f"data: {json.dumps({'type': 'exit', 'exit_code': -1})}\n\n"
                break
                
            # Send all available output in queue
            try:
                while True:
                    stream_type, char = output_queue.get_nowait()
                    last_console_interaction = time.perf_counter()
                    yield f"data: {json.dumps({'type': stream_type, 'text': char})}\n\n"
            except queue.Empty:
                pass
                
            # Check if process is finished
            with active_process_lock:
                if active_process:
                    status = active_process.poll()
                    if status is not None:
                        # Flush remaining queue items
                        try:
                            while True:
                                stream_type, char = output_queue.get_nowait()
                                yield f"data: {json.dumps({'type': stream_type, 'text': char})}\n\n"
                        except queue.Empty:
                            pass
                        
                        yield f"data: {json.dumps({'type': 'exit', 'exit_code': status})}\n\n"
                        break
                        
            time.sleep(0.02)
            
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/console_input', methods=['POST'])
def console_input_api():
    global active_process, last_console_interaction
    data = request.get_json() or {}
    input_val = data.get('input', '')
    last_console_interaction = time.perf_counter()
    
    with active_process_lock:
        if active_process and active_process.poll() is None:
            try:
                active_process.stdin.write(input_val + '\n')
                active_process.stdin.flush()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': f"Failed to write to stdin: {str(e)}"})
                
    return jsonify({'success': False, 'error': 'No active process running'})

@app.route('/api/debug_code', methods=['POST'])
def debug_code_api():
    if not assistant_ref:
        return jsonify({'error': 'Assistant not initialized'}), 503
        
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    output = data.get('output', '').strip()
    language = data.get('language', 'python').strip()
    prompt = data.get('prompt', '').strip()
    
    if not prompt:
        return jsonify({'success': False, 'error': 'No prompt provided'}), 400
        
    try:
        response_text = code_assistant.explain_and_debug_code(code, output, language, prompt)
        return jsonify({
            'success': True,
            'response': response_text
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f"AI Debug exception: {str(e)}"}), 500

class JarvisAssistant:
    def __init__(self):
        self.paused = False
        self.chat_history = []
        self.redirect_info = None
        self.location_target = None
        self.geolocation_service = default_geolocation_service
        self.was_listening = False
        self.speak_queue = Queue()
        self.is_speaking = False
        self.r = sr.Recognizer()
        self.r.dynamic_energy_threshold = True
        self.r.pause_threshold = 0.8
        
        # Start speech worker thread
        threading.Thread(target=self._speech_worker, daemon=True).start()

        try:
            import config as cfg
            self.config = cfg.CONFIG_MAP
        except Exception as e:
            print(f"Error loading centralized config: {e}")
            self.config = {}

        self.keyboard = Controller()
        self.typing_speed = 0.1
        self.typing_active = False
        self.music_dir = "C:\\Users\\hp\\Music"

        genai.configure(api_key=self.config.get('gemini_api_key'))
        self.gemini = genai.GenerativeModel('gemini-2.5-flash')
        
        self.commands = {
            "time": self.get_time,
            "date": self.get_date,
            "get weather": self.get_weather,
            "news": self.get_news,
            "speed test": self.speed_test,
            "system info": self.system_info,
            "screenshot": self.take_screenshot,
            "open": self.open_application,
            "close": self.close_application,
            "search": self.search_google,
            "auto type": self.auto_type,
            "start auto typing": self.auto_type,
            "automation mode": self.automation_mode,
            "web automation": self.automation_mode,
            "screen automation": self.automation_mode,
            "generate qr": self.generate_qr,
            "generate ppt": self.generate_ppt_from_google,
            "search wikipedia": self.wikipedia_search,
            "play music": self.play_music,
            "volume up": self.volume_up,
            "volume down": self.volume_down,
            "mute": self.toggle_mute,
            "unmute": self.toggle_mute,
            "pause music": self.pause_music,
            "next song": self.next_song,
            "previous song": self.previous_song,
            "stop music": self.stop_music,
            "write code": self.generate_code,
            "calculate": self.calculate,
            "write email": self.write_email,
            "wifi password": self.get_wifi_password,
            "storage info": self.get_storage_info,
            "project ideas": self.voice_suggest_ideas,
            "idea engine": self.voice_suggest_ideas,
            "suggest projects": self.voice_suggest_ideas,
            "analyze project": self.analyze_current_project,
            "project health": self.analyze_current_project,
            "plan goal": self.plan_project_goal,
            "decompose goal": self.plan_project_goal
        }

        self.ocr_available = True

        try:
            import uiautomation as auto
            self._ui = auto
            self.ui_available = True
        except Exception:
            self._ui = None
            self.ui_available = False

        self.email_content_draft = None 
        self.from_email_address = self.config.get('gmail_address') 
        self.gmail_password = self.config.get('gmail_password')
        self.recent_responses = []
        self.last_youtube_query = None
        self.notifications = []
        
        # Initialize closed-loop desktop orchestrator, context awareness engine, and idea engine
        self.decision_engine = DecisionEngine(config=self.config)
        self.desktop_orchestrator = DesktopOrchestrator(
            decision_engine=self.decision_engine,
            ui_available=self.ui_available,
            ocr_available=self.ocr_available,
            log_callback=self._log_orchestrator_event,
            speak_callback=self.speak
        )
        self.idea_engine = IdeaEngine(log_callback=self._log_orchestrator_event)
        self.seo_engine = SEOEngine(log_callback=self._log_orchestrator_event)
        self.intelligence = IntelligenceCoordinator(
            idea_engine_ref=self.idea_engine,
            seo_engine_ref=self.seo_engine,
            log_callback=self._log_orchestrator_event
        )
        
        # Purge temporary run files on startup to prevent disk bloat
        try:
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp_run')
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    fp = os.path.join(temp_dir, f)
                    try:
                        if os.path.isfile(fp) or os.path.islink(fp):
                            os.unlink(fp)
                        elif os.path.isdir(fp):
                            shutil.rmtree(fp)
                    except Exception:
                        pass
        except Exception:
            pass


        
        # Start Flask API server
        global assistant_ref
        assistant_ref = self
        threading.Thread(target=self.start_flask, daemon=True).start()

    def start_flask(self):
        try:
            # We open the dashboard after a short delay so the server has time to start
            def open_browser():
                time.sleep(2.0)
                webbrowser.open("http://127.0.0.1:5000")
            threading.Thread(target=open_browser, daemon=True).start()
            
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        except Exception as e:
            print(f"Error starting Flask server: {e}")

    def _speech_worker(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init('sapi5')
            voices = engine.getProperty('voices')
            engine.setProperty('voice', voices[1].id)
        except Exception as e:
            print(f"Error initializing speech engine in worker: {e}")
            engine = None
            
        while True:
            text = self.speak_queue.get()
            if text is None:
                break
            if not engine:
                print(f"Speech Engine offline. Text: {text}")
                self.speak_queue.task_done()
                continue
                
            self.is_speaking = True
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"Speech worker error: {e}")
            finally:
                self.is_speaking = False
                self.speak_queue.task_done()
                
        pythoncom.CoUninitialize()

    def speak(self, text: str):
        """Convert text to speech"""
        try:
            print(f"Assistant: {text}")
        except Exception:
            try:
                print(f"Assistant: {text.encode('ascii', 'ignore').decode('ascii')}")
            except Exception:
                pass

        if hasattr(self, 'recent_responses'):
            self.recent_responses.append(text)
        
        is_api_request = getattr(thread_local, 'is_api_request', False)
        if not is_api_request and hasattr(self, 'notifications'):
            self.notifications.append(text)
            
        self.speak_queue.put(text)

    def listen_single_capture(self):
        """Perform a single Speech-To-Text capture from microphone"""
        try:
            while not self.speak_queue.empty() or self.is_speaking:
                time.sleep(0.1)
            with sr.Microphone() as source:
                self.r.adjust_for_ambient_noise(source, duration=0.8)
                print("[Voice Mode activated] Listening...")
                audio = self.r.listen(source, timeout=5, phrase_time_limit=8)
                query = self.r.recognize_google(audio, language='en-in')
                print(f"User (Voice): {query}")
                return query
        except sr.WaitTimeoutError:
            print("Listening timed out.")
            return "none"
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return "none"

    def listen(self):
        """Listen for voice input"""
        while not self.speak_queue.empty() or self.is_speaking:
            time.sleep(0.1)
            
        with sr.Microphone() as source:
            if self.paused:
                time.sleep(0.5)
                return "none"
                
            print("Listening...")
            try:
                audio = self.r.listen(source, timeout=5)
                query = self.r.recognize_google(audio, language='en-in')
                print(f"User: {query}")
                return query.lower()
                
            except Exception as e:
                print(e)
                return "none"

    def open_application(self, app_name):
        """Open specified application or website dynamically without hardcoded maps."""
        import subprocess
        import shutil
        import webbrowser
        import re
        import os

        target = app_name.strip().lower()
        if not target:
            return

        # 1. Check if the target is a website/URL
        is_website = False
        url = target
        
        web_tlds = [".com", ".net", ".org", ".io", ".ai", ".co", ".info", ".edu", ".gov", ".in"]
        common_sites = ["youtube", "github", "google", "chatgpt", "blackbox", "gemini", "wikipedia", "gmail", "facebook", "twitter", "instagram"]
        
        if target.startswith("http://") or target.startswith("https://"):
            is_website = True
        elif any(tld in target for tld in web_tlds):
            is_website = True
            if not target.startswith("http"):
                url = "https://" + target
        elif any(site in target for site in common_sites):
            is_website = True
            site_name = next(site for site in common_sites if site in target)
            if site_name == "chatgpt":
                url = "https://chat.openai.com"
            elif site_name == "gmail":
                url = "https://mail.google.com"
            else:
                url = f"https://{site_name}.com"

        if is_website:
            try:
                webbrowser.open(url)
                self.speak(f"Opening website {url}")
                return
            except Exception as e:
                self.speak(f"Error opening website: {str(e)}")
                return

        # 2. Desktop application. Determine executable name candidates.
        exe_base = re.sub(r'[^a-zA-Z0-9_\-]', '', target)
        if not exe_base:
            self.speak("Invalid application name.")
            return

        exe_names = [f"{exe_base}.exe", exe_base]
        
        # Apply standard overrides for common app aliases
        if exe_base == "word":
            exe_names.insert(0, "winword.exe")
        elif exe_base == "calculator":
            exe_names.insert(0, "calc.exe")
        elif exe_base == "powerpoint":
            exe_names.insert(0, "powerpnt.exe")
        elif exe_base == "chrome":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            for cp in chrome_paths:
                if os.path.exists(cp):
                    exe_names.insert(0, cp)
                    break
        elif exe_base == "brave":
            brave_paths = [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
            ]
            for bp in brave_paths:
                if os.path.exists(bp):
                    exe_names.insert(0, bp)
                    break

        # Try to find the executable path on system PATH
        for exe in exe_names:
            resolved_path = shutil.which(exe) or (exe if os.path.isabs(exe) and os.path.exists(exe) else None)
            if resolved_path:
                try:
                    subprocess.Popen(resolved_path)
                    self.speak(f"Opening {app_name}")
                    return
                except Exception:
                    pass

        # Last resort fallback: try to execute the binary directly without shell
        for exe in exe_names:
            try:
                os.startfile(exe)
                self.speak(f"Opening {app_name}")
                return
            except Exception:
                try:
                    subprocess.Popen([exe])
                    self.speak(f"Opening {app_name}")
                    return
                except Exception:
                    pass

        self.speak(f"Application {app_name} could not be found or opened.")

    def close_application(self, app_name):
        """Close specified application or website dynamically without hardcoded maps."""
        import win32gui
        import win32con
        import subprocess
        import re
        
        target = app_name.strip().lower()
        if not target:
            return
            
        closed_any = False
        
        def win_enum_callback(hwnd, extra):
            nonlocal closed_any
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                # Check if target name appears in window title
                if target in title:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    closed_any = True
            return True
            
        try:
            win32gui.EnumWindows(win_enum_callback, None)
        except Exception as e:
            print(f"Error enumerating windows for closing: {e}")
            
        if closed_any:
            self.speak(f"Closed windows matching {app_name}")
            return
            
        # Fallback: try soft taskkill with sanitized target executable name
        exe_base = re.sub(r'[^a-zA-Z0-9_\-]', '', target)
        if exe_base:
            exe_names = [f"{exe_base}.exe", exe_base]
            # Common overrides
            if exe_base == "word":
                exe_names.insert(0, "winword.exe")
            elif exe_base == "calculator":
                exe_names.insert(0, "calc.exe")
            elif exe_base == "powerpoint":
                exe_names.insert(0, "powerpnt.exe")
                
            for exe in exe_names:
                try:
                    result = subprocess.run(
                        ['taskkill', '/IM', exe],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if result.returncode == 0:
                        self.speak(f"Closed process {exe}")
                        return
                except Exception:
                    pass
                    
        self.speak(f"Could not find any active window or process for {app_name}")

    def web_search(self, query):
        """Perform web search"""
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        self.speak(f"Searching for {query}")

    def search_web_and_synthesize(self, query: str) -> str:
        """Fetch live web search snippets in real-time and synthesize with LLM"""
        try:
            snippets = []
            try:
                url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                with urllib.request.urlopen(req, timeout=5) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(html, 'html.parser')
                    for res in soup.find_all('div', class_='result'):
                        title_elem = res.find('a', class_='result__a')
                        snippet_elem = res.find('a', class_='result__snippet')
                        if title_elem and snippet_elem:
                            title = title_elem.get_text().strip()
                            snip = snippet_elem.get_text().strip()
                            if title and snip:
                                snippets.append(f"Title: {title}\nSnippet: {snip}")
                        if len(snippets) >= 4:
                            break
            except Exception as search_err:
                logger.warning(f"Live web search snippet fetch error: {search_err}")

            # Synthesize answer using live search data
            if snippets:
                raw_context = "\n\n".join(snippets)
                clean_context = raw_context.encode('ascii', errors='ignore').decode('ascii')
                prompt = (
                    f"User Question: {query}\n\n"
                    f"Live Web Search Information:\n{clean_context}\n\n"
                    f"Based on the real-time search information above, provide a direct, helpful, and concise answer to the user's question in plain text. Do not use asterisks or markdown bolding."
                )
                answer = self.query_groq(prompt)
                if answer:
                    clean_ans = answer.replace("*", "").strip()
                    return clean_ans.encode('ascii', errors='ignore').decode('ascii')

            # Fallback to direct LLM knowledge
            fallback = self.query_groq(f"Answer this question directly and concisely: {query}")
            return fallback.encode('ascii', errors='ignore').decode('ascii')
        except Exception as e:
            logger.error(f"Search synthesis error: {e}")
            return f"I encountered an issue processing search results for {query}."

    def search_google(self, query: str):
        """Search Google and synthesize real-time web results with AI"""
        try:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
            self.speak(f"Searching Google for {query}")
            
            # Fetch live web results and speak synthesized response
            answer = self.search_web_and_synthesize(query)
            if answer:
                self.speak(answer)
        except Exception as e:
            self.speak(f"Error searching Google: {str(e)}")

    def system_info(self):
        """Get system information"""
        info = f"Operating System: {platform.system()} {platform.version()}\n"
        info += f"CPU: {platform.processor()}\n"
        info += f"RAM: {round(psutil.virtual_memory().total / (1024**3))}GB\n"
        info += f"CPU Usage: {psutil.cpu_percent()}%\n"
        info += f"Memory Usage: {psutil.virtual_memory().percent}%"
        self.speak(info)

    def run_diagnostics(self):
        """Perform a comprehensive system diagnostic check and speak results"""
        try:
            import psutil
            import subprocess
            import platform
            import re
            
            cpu_usage = round(_cpu_cached, 1)
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            
            # Disk space check
            free_disk = 0
            try:
                usage = psutil.disk_usage('C:\\')
                free_disk = round(usage.free / (1024**3), 1)
            except Exception:
                pass
            
            # Battery check
            battery_text = ""
            if hasattr(psutil, "sensors_battery"):
                battery = psutil.sensors_battery()
                if battery:
                    percent = battery.percent
                    power_plugged = battery.power_plugged
                    if power_plugged:
                        battery_text = f"Battery is fully plugged and charging at {percent}%" if percent < 100 else "Battery is plugged and fully charged"
                    else:
                        battery_text = f"Battery level is at {percent}% and discharging"
                else:
                    battery_text = "System power is connected directly to mains"
            else:
                battery_text = "System power is nominal"
                
            # Ping test (Google DNS 8.8.8.8)
            ping_text = "Network connection is active"
            ping_val = None
            try:
                # Run a single quick ping
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output("ping -n 1 8.8.8.8", startupinfo=startupinfo, timeout=2.0).decode('utf-8', errors='ignore')
                match = re.search(r"time=(\d+)ms", output)
                if match:
                    ping_val = int(match.group(1))
                    ping_text = f"Network latency is {ping_val} milliseconds"
            except Exception:
                ping_text = "Network reports high latency or packet loss"
                
            # Active processes
            active_procs = len(psutil.pids())
            
            report = f"Starting full system diagnostic sweep, Sir.\n"
            report += f"CPU core usage is currently at {cpu_usage}%.\n"
            report += f"System memory load is at {ram_percent}%.\n"
            report += f"Storage on C drive has {free_disk} gigabytes remaining.\n"
            report += f"{battery_text}, Sir.\n"
            report += f"{ping_text}.\n"
            report += f"Active process count is {active_procs}.\n"
            report += "All arrays are operating within nominal parameters. J.A.R.V.I.S. is fully operational, Sir."
            
            self.speak(report)
            return report
        except Exception as e:
            err = f"Diagnostic sweep interrupted by error: {str(e)}"
            self.speak(err)
            return err

    def get_active_window_details(self):
        """Retrieves metadata and bounding coordinates of the currently active foreground window"""
        return ObservationEngine.get_active_window_details()

    def analyze_screenshot_ocr(self, img_path='active_window.png'):
        """Runs NVIDIA Nemotron OCR v2 on the specified image and returns detected text and bounding boxes"""
        try:
            import os
            import base64
            from PIL import Image
            import io
            if not os.path.exists(img_path):
                return {"error": f"Image file {img_path} does not exist"}
            img = Image.open(img_path)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=80)
            image_b64 = base64.b64encode(buf.getvalue()).decode()
            if len(image_b64) >= 180000:
                w, h = img.size
                target_w = 1280 if w > 1280 else w
                target_h = int(h * (target_w / w))
                img_resized = img.resize((target_w, target_h))
                buf = io.BytesIO()
                img_resized.save(buf, format='JPEG', quality=75)
                image_b64 = base64.b64encode(buf.getvalue()).decode()
            return OCRService.perform_ocr(image_b64)
        except Exception as e:
            return {"error": str(e)}

    def _log_orchestrator_event(self, stage: str, message: str):
        # Filter internal background subsystem logs from popping up in the user chat
        internal_stages = {
            "MEMORY", "SKILL", "STACK_ANALYZER", "QUALITY_CONTROL", 
            "SCORING", "RANKING", "COORDINATOR_INIT", "COORDINATOR",
            "IDEA_ENGINE", "IDEA_GENERATOR", "PROMPT_ENGINE", "PROJECT_ANALYZER"
        }
        if stage in internal_stages:
            return
        if hasattr(self, 'notifications'):
            self.notifications.append(f"[{stage}] {message}")

    def get_current_context(self):
        """Captures environmental observation, runs perception, and builds structured ContextState."""
        obs = ObservationEngine.observe(capture_images=False)
        per = PerceptionEngine.perceive(
            ui_available=self.ui_available,
            ocr_available=self.ocr_available,
            observation=obs,
            image_path=obs.active_window_screenshot_path or "active_window.png"
        )
        return ContextEngine.build_context(obs, per)

    def get_context_summary(self) -> dict:
        """Returns JSON-serializable dictionary of current context awareness state."""
        return self.get_current_context().to_dict()

    def run_desktop_task(self, goal: str) -> dict:
        """Executes a user goal using the canonical closed-loop orchestrator."""
        return self.desktop_orchestrator.run_task(goal)

    def voice_suggest_ideas(self):
        """Voice-triggered prompt asking the user for their stack and generating recommendations."""
        self.speak("Which technologies or languages would you like to build with?")
        stack_input = self.take_command()
        if not stack_input or stack_input == "None":
            self.speak("I didn't catch the technologies. You can also explore project concepts in the web dashboard Idea Engine.")
            return

        techs = [t.strip() for t in stack_input.replace("and", ",").split(",") if t.strip()]
        self.speak(f"Analyzing project opportunities for {', '.join(techs)}...")
        req = IdeaGenerationRequest(
            technologies=techs,
            mode=GenerationMode.STACK_TO_IDEAS,
            number_of_ideas=3
        )
        res = self.idea_engine.generate_ideas(req)
        if res.success and res.top_recommendation:
            top = res.top_recommendation
            summary = f"Top recommended project: {top.title}, with a score of {top.score.overall_score} out of 100. {top.one_line_pitch}."
            self.speak(summary)
            print(summary)
        else:
            self.speak("I was unable to generate project ideas right now. Please check the web console.")

    def get_perception_clickable_controls(self):
        """Combines UI Automation controls with NVIDIA Nemotron OCR detections to map all clickable targets"""
        return PerceptionEngine.get_perception_data(self.ui_available, self.ocr_available)

    def generate_proposed_plan(self, instruction):
        """Generates a proposed JSON action plan for a user instruction based on the current active window state"""
        try:
            import json
            import requests
            
            # 1. Gather current UI state
            ui_state = self.get_perception_clickable_controls()
            window_details = self.get_active_window_details()
            
            # Construct LLM prompt
            prompt = (
                f"You are J.A.R.V.I.S., the task planner. The user wants to perform this task: \"{instruction}\"\n\n"
                f"Here is the active window state metadata:\n"
                f"Active Window Title: {window_details.get('title')}\n"
                f"Active Process: {window_details.get('process_name')}\n"
                f"Window Bounds: {window_details.get('bounds')}\n\n"
                f"Clickable Controls found via UI Automation:\n"
                f"{json.dumps(ui_state.get('ui_automation_controls', []), indent=2)}\n\n"
                f"Text elements found via OCR:\n"
                f"{json.dumps(ui_state.get('ocr_detections', []), indent=2)}\n\n"
                "Task: Generate a proposed sequence of desktop actions to accomplish the user's task.\n"
                "CRITICAL: Do NOT execute any actions. Simply generate the plan.\n\n"
                "Output Format:\n"
                "You must respond ONLY with a valid JSON array. Each element of the array must be an object representing a step, containing:\n"
                "- \"action\": one of \"click\", \"type\", \"hotkey\", \"wait\", \"scroll\", \"drag\".\n"
                "- \"target\": the label, name, coordinates, or text of the control to target.\n"
                "- \"confidence\": a float representing confidence (0.0 to 1.0).\n"
                "- \"reasoning\": why this action is selected.\n"
                "- \"expected_result\": what should happen after this action is completed.\n\n"
                "Do not include markdown blocks or other text. Respond with raw JSON."
            )
            
            content = self.query_llm_with_fallback(
                system_prompt="You are a structured desktop task planner. You output only raw JSON arrays.",
                messages_history=[],
                user_prompt=prompt,
                response_format_json=True
            )
            # Clean up any potential markdown wrap
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            try:
                return json.loads(content)
            except Exception:
                return {"error": "Failed to parse planner LLM response as JSON", "raw_response": content}
                
        except Exception as e:
            return {"error": str(e)}

    def take_screenshot(self):
        """Take screenshot"""
        pyautogui.screenshot('screenshot.png')
        self.speak("Screenshot taken")

    def shutdown_pc(self):
        """Shutdown computer"""
        self.speak("Shutting down computer")
        os.system("shutdown /s /t 1")

    def restart_pc(self):
        """Restart computer"""
        self.speak("Restarting computer")
        os.system("shutdown /r /t 1")

    def lock_pc(self):
        """Lock computer"""
        self.speak("Locking computer")
        os.system("rundll32.exe user32.dll,LockWorkStation")

    def wikipedia_search(self, query):
        """Search Wikipedia"""
        try:
            result = wikipedia.summary(query, sentences=2)
            self.speak(f"According to Wikipedia: {result}")
        except wikipedia.exceptions.WikipediaException:
            self.speak("Error searching Wikipedia")

    def get_time(self):
        """Get current time"""
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        self.speak(f"The current time is {current_time}")

    def get_date(self):
        """Get current date"""
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        self.speak(f"Today's date is {current_date}")

    def auto_type(self):
        """Voice controlled typing with commands"""
        self.typing_active = True
        self.speak("Voice typing activated. Say 'stop typing' to end.")

        while self.typing_active:
            command = self.listen()
            
            if command == "none":
                continue

            if "stop typing" in command.lower():
                self.typing_active = False
                self.speak("Voice typing stopped")
                break

            # Type out the command
            for char in command:
                if not self.typing_active:  
                    break
                self.keyboard.press(char)
                self.keyboard.release(char)
                time.sleep(self.typing_speed)
        
            # Add a space after each phrase
            self.keyboard.press(' ')
            self.keyboard.release(' ')

    def set_typing_speed(self, speed="normal"):
        """Set typing speed (slow/normal/fast)"""
        speeds = {
            "slow": 0.2,
            "normal": 0.1,
            "fast": 0.05
        }
        if speed in speeds:
            self.typing_speed = speeds[speed]
            self.speak(f"Typing speed set to {speed}")

    def auto_retry(max_attempts=3, delay=1):
        """Decorator for automatic error handling and retry"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                attempts = 0
                while attempts < max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except requests.RequestException as e:
                        attempts += 1
                        print(f"Network error (attempt {attempts}/{max_attempts}): {e}")
                        if attempts < max_attempts:
                            time.sleep(delay)
                    except json.JSONDecodeError:
                        print("Invalid response from weather API")
                        return None
                    except Exception as e:
                        print(f"Unexpected error: {e}")
                        return None
                return None
            return wrapper
        return decorator

    @auto_retry(max_attempts=3)
    def get_weather(self, city=None, type_mode: bool = False):
        """Get weather information for a city with auto-retry"""
        try:
            api_key = self.config.get('weather_api_key')
            if not api_key:
                self.speak("Weather API key not found in config file")
                return

            while True:
                if not city:
                    if type_mode:
                        print("Which city's weather would you like to know?")
                        city = input().lower()
                    else:
                        self.speak("Which city's weather would you like to know?")
                        city = self.listen()

                if not city or city == "none":
                    self.speak("I couldn't understand the city name. Please try again or say 'cancel' to stop.")
                    city = None
                    continue

                if "cancel" in city.lower():
                    self.speak("Weather request cancelled")
                    return

                url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    temp = data['main']['temp']
                    humidity = data['main']['humidity']
                    desc = data['weather'][0]['description']

                    weather_info = f"Weather in {city}:\n"
                    weather_info += f"Temperature: {temp}Â°C\n"
                    weather_info += f"Humidity: {humidity}%\n"
                    weather_info += f"Conditions: {desc}"

                    self.speak(weather_info)
                    break
                else:
                    self.speak(f"Could not find weather data for {city}. Please try another city or say 'cancel' to stop.")
                    city = None

        except Exception as e:
            self.speak(f"Error getting weather: {str(e)}")

    def get_news(self):
        """Get latest news headlines"""
        try:
            api_key = self.config.get('news_api_key')
            if not api_key:
                self.speak("News API key not found in config file")
                return

            url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200:
                articles = data['articles'][:5]  # Get top 5 news articles
                news = "Here are the top news headlines:\n"
                for article in articles:
                    news += f"- {article['title']}\n"

                print(news)
                self.speak(news)
            else:
                self.speak("Error getting news")

        except Exception as e:
            self.speak(f"Error: {str(e)}")

    def speed_test(self):
        """Perform internet speed test"""
        try:
            st = speedtest.Speedtest()
            st.download()
            st.upload()
            ping = st.results.ping
            download_speed = st.results.download / 1_000_000  # Convert to Mbps
            upload_speed = st.results.upload / 1_000_000  # Convert to Mbps

            speed_info = f"Ping: {ping} ms\n"
            speed_info += f"Download speed: {download_speed:.2f} Mbps\n"
            speed_info += f"Upload speed: {upload_speed:.2f} Mbps"

            print(speed_info)
            self.speak(speed_info)

        except Exception as e:
            self.speak(f"Error: {str(e)}")

    def generate_qr(self):
        """Run qr.py to generate QR code"""
        try:
            self.speak("Generating QR code")
            subprocess.run([sys.executable, 'qr.py'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.speak("QR code has been generated")
        except Exception as e:
            self.speak(f"Error generating QR code: {str(e)}")

    def generate_ppt_from_google(self):
        """Generate a PPT from live Google results"""
        try:
            self.speak("Opening PPT generator")
            path = ppt_generator.run_ppt_gui()
            if path:
                self.speak(f"Presentation created: {os.path.basename(path)}")
            else:
                self.speak("PPT creation cancelled or failed")
        except Exception as e:
            self.speak(f"Error generating presentation: {str(e)}")



    def take_typed_command(self):
        """Get command through text input"""
        try:
            print("Type your command: ", end='')
            return input().strip()
        except Exception as e:
            print(f"Error in type mode: {e}")
            return "none"

    def generate_qr_with_text(self, text: str):
        """Generate QR code directly with text and save it to the project directory"""
        try:
            import qrcode
            import time
            ts = time.strftime("%Y%m%d_%H%M%S")
            fname = f"qr_{ts}.png"
            img = qrcode.make(text)
            img.save(fname)
            self.speak(f"QR code generated and saved as {fname}")
            print(f"\n--- QR Code Generated ---\nSaved as: {os.path.abspath(fname)}\n")
        except Exception as e:
            self.speak(f"Error generating QR code: {str(e)}")

    def analyze_current_project(self):
        """Run project health and security analyzer on current codebase"""
        try:
            self.speak("Analyzing local codebase and security posture, Sir.")
            report = self.intelligence.analyze_project(".")
            summary = f"Project analysis complete. Overall Health is {report.scores.overall:.0f} out of 100 with {len(report.findings)} findings recorded."
            self.speak(summary)
            return report
        except Exception as e:
            self.speak(f"Unable to complete project analysis: {str(e)}")

    def plan_project_goal(self, goal: str = "Build modern architecture"):
        """Decompose a high-level goal into dependency-ordered tasks"""
        try:
            self.speak(f"Decomposing objective: {goal}")
            plan = self.intelligence.decompose_goal(goal)
            self.speak(f"Goal broken down into {len(plan.tasks)} structured tasks.")
            return plan
        except Exception as e:
            self.speak(f"Failed to plan goal: {str(e)}")

    def query_llm_with_fallback(self, system_prompt, messages_history, user_prompt, response_format_json=False):
        """
        Delegates LLM completion queries to the shared LLMService helper.
        """
        return LLMService.query_llm_with_fallback(
            config=self.config,
            system_prompt=system_prompt,
            messages_history=messages_history,
            user_prompt=user_prompt,
            response_format_json=response_format_json
        )

    def query_groq_intent(self, command: str) -> dict:
        """Helper to classify user intent and route to command or chat using Groq"""
        try:
            api_key = self.config.get('groq_api_key')
            if not api_key:
                return {"intent": "chat", "response": "Groq API key not configured."}
                
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            
            system_prompt = (
                "You are J.A.R.V.I.S., a premium digital assistant. The current year is 2026.\n"
                "The user will send you a message. Analyze their intent.\n"
                "Decide if the user wants to execute one of the specific system commands listed below, or if they are just chatting/asking a question.\n\n"
                "Available System Commands:\n"
                "- \"system_info\": Get system information/specifications.\n"
                "- \"system_diagnostics\": Perform a comprehensive system diagnostics scan and systems check.\n"
                "- \"take_screenshot\": Take a screenshot of the computer screen.\n"
                "- \"open_app\": Open a specific application. Requires parameter: 'app_name' (e.g. 'notepad', 'chrome', etc.). Optionally takes parameter: 'write_content' (if the user asks to write/type an essay, message, text, or content inside the app, generate that requested content and place it in the 'write_content' parameter).\n"
                "- \"close_app\": Close a specific application. Requires parameter: 'app_name'.\n"
                "- \"web_automation\": Start web or screen automation mode.\n"
                "- \"google_search\": Search Google. Requires parameter: 'query'. IMPORTANT: You must select this command if the user asks a question about facts, events, real-time data, or people you do not know, or that occurred/developed after your knowledge cutoff (December 2023). Do not reply conversationally with 'I don't know' or guess; instead, route to google_search. Also, if the user uses pronouns or references to previous context (like 'search for him', 'look up that'), resolve the reference to the actual entity from the conversation history and search for that entity.\n"
                "- \"wikipedia_search\": Search Wikipedia. Requires parameter: 'query'.\n"
                "- \"shutdown_pc\": Shut down the computer.\n"
                "- \"restart_pc\": Restart the computer.\n"
                "- \"lock_pc\": Lock the computer.\n"
                "- \"weather\": Check weather. Optional parameter: 'city'.\n"
                "- \"news\": Get current news headlines.\n"
                "- \"speed_test\": Run an internet speed test.\n"
                "- \"analyze_project\": Inspect codebase health, architecture, security, and dependencies.\n"
                "- \"plan_goal\": Decompose an engineering or project objective into tasks. Requires parameter: 'goal'.\n"
                "- \"stop_motion\": Stop motion tracking.\n"
                "- \"generate_qr\": Open the QR code generator modal. Optionally takes parameter: 'text' (the URL or text to encode).\n"
                "- \"generate_ppt\": Open the PowerPoint presentation builder modal. Optionally takes parameter: 'topic'.\n"
                "- \"write_code\": Write code, generate code, script, program, or ask for coding/programming help. Requires parameters: 'prompt' (the full code generation query), and optionally 'language' (must be strictly one of these exact values: 'python', 'javascript', 'html', 'css', 'cpp', 'java', 'csharp', 'go', 'typescript', 'sql', 'rust'). Default language to 'python' if not specified.\n"
                "- \"email_assistant\": Open or launch the email assistant composer modal. Optionally takes parameters: 'to' (the recipient name or role) and 'purpose' (what the email is about).\n"
                "- \"wifi_password\": Show the current connected WiFi network password.\n"
                "- \"play_music\": Play music or play a specific song. Optional parameter: 'song_name'.\n"
                "- \"pause_music\": Pause music playback.\n"
                "- \"stop_music\": Stop music playback.\n"
                "- \"next_song\": Play next song.\n"
                "- \"previous_song\": Play previous song.\n"
                "- \"volume_up\": Turn up system volume.\n"
                "- \"volume_down\": Turn down system volume.\n"
                "- \"toggle_mute\": Mute or unmute system volume.\n"
                "- \"storage_info\": Check storage drive space details.\n\n"
                "CRITICAL INSTRUCTIONS ON WEB SEARCH FALLBACK & CONTEXT:\n"
                "1. If the user asks a question about facts, events, real-time data, or people that you do not know, or that occurred/developed after December 2023, you MUST classify the intent as 'command' and command as 'google_search'. Do not guess or answer conversationally (e.g., do not say 'I don't know' or 'I couldn't find information').\n"
                "2. If the user explicitly asks to search Google (e.g. 'search google for X', 'search for him in google'), route to 'google_search'.\n"
                "3. RESOLVE PRONOUNS: If the user refers to previous context using pronouns (e.g., 'search for him', 'who is he', 'tell me about it'), resolve the pronoun/reference using the conversation history. For example, if the user asked 'who is neev lila' and now says 'search for him', route to 'google_search' with the parameter 'query' set to 'neev lila'.\n\n"
                "4. LATEST MESSAGE FOCUS: You must classify the intent of the LATEST user message (the last message in the history). Do NOT repeat previous commands or carry over previous intents unless the latest message is a clear pronoun/context reference (like 'search for him'). If the latest message does not match a command (e.g. general conversational remarks, clear/reset requests that bypassed deterministic routing, etc.), do not execute a command; classify it as 'chat' instead.\n\n"
                "Response Format:\n"
                "You must respond ONLY with a valid JSON object. Do not include markdown code blocks (```json ... ```) or conversational preambles/postambles. Respond only with the raw JSON string.\n"
                "If the intent is a system command, respond with:\n"
                "{\n"
                "  \"intent\": \"command\",\n"
                "  \"command\": \"<command_name>\",\n"
                "  \"params\": { ... }\n"
                "}\n\n"
                "If the intent is general chat, asking a question, or cannot be mapped to a command, respond with:\n"
                "{\n"
                "  \"intent\": \"chat\",\n"
                "  \"response\": \"<your conversational response to the user's message here. You must strictly mimic J.A.R.V.I.S., Tony Stark's premium AI digital butler. Speak in a highly polite, sophisticated, loyal, slightly witty British-English tone. Always address the user as 'Sir' or 'Ma'am'. Refer to system hardware and databases as 'my arrays', 'our mainframes', and 'telemetry' where appropriate. Never use asterisks or markdown tags.>\"\n"
                "}"
            )
            
            messages_history = list(self.chat_history)
            # If the current command is not already the last message in history, pop it so we pass it as user_prompt
            if messages_history and messages_history[-1].get("content") == command:
                messages_history.pop()
            
            res_text = self.query_llm_with_fallback(
                system_prompt=system_prompt,
                messages_history=messages_history,
                user_prompt=command,
                response_format_json=True
            )
            
            # Parse JSON
            import json
            return json.loads(res_text)
        except Exception as e:
            print(f"Error classifying intent with fallback pipeline: {e}")
            return None

    def process_command_with_mode(self, command, type_mode=False):
        try:
            cmd_lower = command.lower().strip()
            if not cmd_lower:
                return False

            # Check for clear/reset chat commands
            is_clear_cmd = (
                ("clear" in cmd_lower and any(w in cmd_lower for w in ["chat", "conversation", "history"])) or
                ("reset" in cmd_lower and any(w in cmd_lower for w in ["chat", "conversation", "history"])) or
                cmd_lower in ["clear", "reset", "start fresh", "clean chat", "clean conversation"]
            )
            if is_clear_cmd:
                self.chat_history = []
                self.redirect_info = {
                    "action": "clear_chat"
                }
                self.speak("I have cleared our conversation history, Sir. Let's start fresh.")
                return False

            # Append user command to history
            self.chat_history.append({"role": "user", "content": command})
            # Keep history to last 20 messages (10 turns) to prevent context explosion
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]

            # Run the actual command processing
            should_exit = self._process_command_with_mode_inner(command, type_mode)

            # Append assistant response to history
            response_text = " ".join(self.recent_responses)
            if response_text:
                self.chat_history.append({"role": "assistant", "content": response_text})
                if len(self.chat_history) > 20:
                    self.chat_history = self.chat_history[-20:]

            return should_exit
        except Exception as e:
            self.speak(f"Error processing command wrapper: {str(e)}")
            return False

    def _process_command_with_mode_inner(self, command, type_mode=False):
        try:
            cmd_lower = command.lower().strip()
            if not cmd_lower:
                return False

            # Check if command starts with "nova" (strip it so both direct and nova queries are processed same)
            if cmd_lower.startswith("nova"):
                command = command[4:].strip()
                cmd_lower = command.lower().strip()

            # 0. Fast-pass routing for Global Intelligence Globe & Geolocation
            # 0.1 Globe Target Reset / Clear
            if cmd_lower in ["reset globe", "clear target", "reset target", "clear globe", "reset map", "clear map", "clear target marker"]:
                self.location_target = {"action": "reset"}
                self.speak("Global intelligence target cleared. Earth visualization returned to idle positioning.")
                return False

            # 0.2 Geolocation / IP Geolocation Detection (Highest Priority)
            geo_intent = IPIntentDetector.detect_intent(command)
            if geo_intent:
                ip_str, intent_type = geo_intent
                service = getattr(self, 'geolocation_service', default_geolocation_service)
                geo_result = service.lookup(ip_str)
                chat_msg = GeolocationSynthesizer.build_chat_response(geo_result)
                self.location_target = geo_result.to_dict()
                self.speak(chat_msg)
                return False

            # Fast-pass YouTube download check (any command containing "download")
            if "download" in cmd_lower:
                download_query = None
                
                # Strip all possible command prefixes to get the raw song name
                temp_query = cmd_lower
                prefixes = [
                    "hey bro can you download the song", "hey bro can you download song", "hey bro can you download the", "hey bro can you download",
                    "can you download the song", "can you download song", "can you download the", "can you download",
                    "download from youtube", "download video from youtube", "download the video", "download the song", "download that song",
                    "download it using yt-dlp", "download using yt-dlp", "download it using ytdlp", "download using ytdlp",
                    "download it", "download this", "download that", "download"
                ]
                # Sort prefixes by length descending so longer patterns are matched and stripped first
                prefixes.sort(key=len, reverse=True)
                for prefix in prefixes:
                    temp_query = re.sub(r'(?i)\b' + re.escape(prefix) + r'\b', '', temp_query).strip()
                
                # Check for other noise words/sites
                for word in ["youtube", "video", "song", "using yt-dlp", "using ytdlp", "yt-dlp", "ytdlp"]:
                    temp_query = re.sub(r'(?i)\b' + re.escape(word) + r'\b', '', temp_query).strip()
                
                if temp_query:
                    download_query = temp_query
                
                # If no specific query was extracted from this command, fallback to the last searched youtube query
                if not download_query and hasattr(self, 'last_youtube_query') and self.last_youtube_query:
                    download_query = self.last_youtube_query
                
                if download_query:
                    clean_download_query = " ".join(word.capitalize() for word in download_query.split())
                    self.speak(f"Searching for {clean_download_query} to download...")
                    threading.Thread(target=self.download_youtube_video, args=(clean_download_query,), daemon=True).start()
                    return False
                else:
                    self.speak("I don't know which video you want me to download, Sir. Please specify the name.")
                    return False

            # Fast-pass YouTube multitasking check (e.g. "open youtube and play song X" or "play X on youtube")
            if "youtube" in cmd_lower and any(x in cmd_lower for x in ["play", "plays", "playing", "search", "searches", "searching", "song"]):
                # Extract clean song/search query by stripping command wrapper prefixes
                query = cmd_lower
                prefixes = [
                    "open youtube and play the song", "open youtube and play song", "open youtube and play the", "open youtube and play",
                    "open youtube and plays the song", "open youtube and plays song", "open youtube and plays the", "open youtube and plays",
                    "open youtube and search for", "open youtube and search", "open youtube and",
                    "play on youtube", "plays on youtube", "playing on youtube",
                    "search on youtube", "searches on youtube", "searching on youtube",
                    "play song", "play the song", "play the", "play",
                    "plays song", "plays the song", "plays the", "plays",
                    "playing song", "playing the song", "playing the", "playing",
                    "search for", "search", "searches for", "searches", "searching for", "searching", "youtube"
                ]
                for prefix in prefixes:
                    query = re.sub(r'(?i)\b' + re.escape(prefix) + r'\b', '', query).strip()
                
                # If there's a residual search query, open it in browser search
                if query:
                    import urllib.parse
                    import requests
                    clean_query = " ".join(word.capitalize() for word in query.split())
                    self.speak(f"Playing {clean_query} on YouTube")
                    self.last_youtube_query = clean_query
                    
                    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        }
                        response = requests.get(search_url, headers=headers, timeout=5)
                        if response.status_code == 200:
                            matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', response.text)
                            if matches:
                                # Retrieve unique matches to skip duplicates/playlist links and get the first video
                                unique_matches = []
                                for m in matches:
                                    if m not in unique_matches:
                                        unique_matches.append(m)
                                video_id = unique_matches[0]
                                webbrowser.open(f"https://www.youtube.com/watch?v={video_id}")
                                return False
                        webbrowser.open(search_url)
                    except Exception:
                        webbrowser.open(search_url)
                    return False

            # UI modals & Code Assistant fast-pass routing
            # A. PPT Creator Modal
            if any(x in cmd_lower for x in ["create ppt", "generate ppt", "launch ppt", "open ppt"]):
                topic = ""
                for prefix in ["create ppt on ", "generate ppt on ", "create ppt about ", "generate ppt about "]:
                    if prefix in cmd_lower:
                        idx = cmd_lower.find(prefix)
                        topic = command[idx + len(prefix):].strip()
                        break
                
                if type_mode:
                    self.redirect_info = {
                        "action": "redirect_ppt_creator",
                        "topic": topic
                    }
                    self.speak("Redirecting to Presentation Builder...")
                else:
                    self.generate_ppt_from_google()
                return False

            # B. QR Code Utility Modal
            if any(x in cmd_lower for x in ["create qr", "generate qr", "open qr", "launch qr"]):
                text = ""
                for prefix in ["create qr for ", "generate qr for ", "create qr code for ", "generate qr code for "]:
                    if prefix in cmd_lower:
                        idx = cmd_lower.find(prefix)
                        text = command[idx + len(prefix):].strip()
                        break
                
                if type_mode:
                    self.redirect_info = {
                        "action": "redirect_qr_generator",
                        "text": text
                    }
                    self.speak("Redirecting to QR Code Utility...")
                else:
                    if text:
                        self.generate_qr_with_text(text)
                    else:
                        self.generate_qr()
                return False

            # C. Email Assistant Modal
            if any(x in cmd_lower for x in ["write email", "create email", "email assistant", "open email", "launch email", "draft email"]):
                to = ""
                purpose = ""
                for prefix in ["write email to ", "create email to ", "draft email to ", "email to "]:
                    if prefix in cmd_lower:
                        idx = cmd_lower.find(prefix)
                        rest = command[idx + len(prefix):].strip()
                        for marker in [" asking for ", " about ", " to "]:
                            if marker in rest.lower():
                                m_idx = rest.lower().find(marker)
                                to = rest[:m_idx].strip()
                                purpose = rest[m_idx + len(marker):].strip()
                                break
                        if not to:
                            to = rest
                        break
                if not purpose:
                    for prefix in [" asking for ", " about "]:
                        if prefix in cmd_lower:
                            idx = cmd_lower.find(prefix)
                            purpose = command[idx + len(prefix):].strip()
                            break
                
                if type_mode:
                    self.redirect_info = {
                        "action": "redirect_email_assistant",
                        "to": to,
                        "purpose": purpose
                    }
                    self.speak("Redirecting to Email Assistant...")
                else:
                    self.speak("Please use the dashboard email assistant to draft your email.")
                return False

            # D. Code Assistant (write_code)
            is_code_request = False
            detected_lang = "python"
            languages = ['python', 'javascript', 'html', 'css', 'cpp', 'java', 'csharp', 'go', 'typescript', 'sql', 'rust']
            code_keywords = ["write code", "generate code", "write a code", "write script", "write program", "code in ", "code to ", "script to ", "program to ", "code for "]
            
            is_creative_script = any(w in cmd_lower for w in ["youtube", "video", "movie", "play", "story", "dialogue", "speech", "outline", "skit", "creative"])
            if not is_creative_script:
                if any(x in cmd_lower for x in code_keywords) or any(f"{lang} code" in cmd_lower for lang in languages) or any(f"code in {lang}" in cmd_lower for lang in languages) or (cmd_lower.startswith("write a ") and any(lang in cmd_lower for lang in languages)):
                    is_code_request = True
                
            if is_code_request:
                for lang in languages:
                    if lang in cmd_lower:
                        detected_lang = lang
                        break
                    if lang == "cpp" and "c++" in cmd_lower:
                        detected_lang = "cpp"
                        break
                    if lang == "csharp" and "c#" in cmd_lower:
                        detected_lang = "csharp"
                        break
                    if lang == "javascript" and " js" in cmd_lower:
                        detected_lang = "javascript"
                        break
                    if lang == "typescript" and " ts" in cmd_lower:
                        detected_lang = "typescript"
                        break
                
                if type_mode:
                    self.redirect_info = {
                        "action": "redirect_code_assistant",
                        "prompt": command,
                        "language": detected_lang
                    }
                    self.speak("Redirecting to Code Assistant...")
                else:
                    self.speak("Code generation requested. Please use the Code Assistant panel for code writing.")
                return False

            # 1. Try LLM-based intent routing first
            intent_data = self.query_groq_intent(command)
            if intent_data and isinstance(intent_data, dict):
                intent = intent_data.get("intent")
                if intent == "chat":
                    resp = intent_data.get("response", "")
                    # Clean asterisks from chat response
                    resp = resp.replace("**", "").replace("*", "")
                    self.speak(resp)
                    return False
                elif intent == "command":
                    cmd_name = intent_data.get("command")
                    params = intent_data.get("params", {})
                    
                    print(f"Routing to system command: {cmd_name} with params: {params}")
                    
                    if cmd_name == "system_info":
                        self.system_info()
                        return False
                    elif cmd_name == "system_diagnostics":
                        self.run_diagnostics()
                        return False
                    elif cmd_name == "take_screenshot":
                        self.take_screenshot()
                        return False
                    elif cmd_name == "open_app":
                        app = params.get("app_name", "").strip()
                        write_content = params.get("write_content", "").strip()
                        if app:
                            self.smart_open_application(app, write_content)
                        return False
                    elif cmd_name == "close_app":
                        app = params.get("app_name", "").strip()
                        if app:
                            self.smart_close_application(app)
                        return False
                    elif cmd_name == "web_automation":
                        self.automation_mode()
                        return False
                    elif cmd_name == "google_search":
                        query = params.get("query", "").strip()
                        if query:
                            self.search_google(query)
                        return False
                    elif cmd_name == "wikipedia_search":
                        query = params.get("query", "").strip()
                        if query:
                            self.wikipedia_search(query)
                        return False
                    elif cmd_name == "shutdown_pc":
                        self.shutdown_pc()
                        return False
                    elif cmd_name == "restart_pc":
                        self.restart_pc()
                        return False
                    elif cmd_name == "lock_pc":
                        self.lock_pc()
                        return False
                    elif cmd_name == "weather":
                        city = params.get("city", "").strip()
                        if city:
                            self.get_weather(city, type_mode)
                        else:
                            self.get_weather(type_mode=type_mode)
                        return False
                    elif cmd_name == "news":
                        self.get_news()
                        return False
                    elif cmd_name == "speed_test":
                        self.speed_test()
                        return False
                    elif cmd_name == "track_motion":
                        if not self.motion_tracking_active:
                            self.toggle_motion_tracking()
                        else:
                            self.speak("Motion tracking is already active")
                        return False
                    elif cmd_name == "stop_motion":
                        if self.motion_tracking_active:
                            self.toggle_motion_tracking()
                        else:
                            self.speak("Motion tracking is not active")
                        return False
                    elif cmd_name == "generate_qr":
                        text = params.get("text", "").strip()
                        if type_mode:
                            self.redirect_info = {
                                "action": "redirect_qr_generator",
                                "text": text
                            }
                            self.speak("Redirecting to QR Code Utility...")
                        else:
                            if text:
                                self.generate_qr_with_text(text)
                            else:
                                self.generate_qr()
                        return False
                    elif cmd_name == "generate_ppt":
                        topic = params.get("topic", "").strip()
                        if type_mode:
                            self.redirect_info = {
                                "action": "redirect_ppt_creator",
                                "topic": topic
                            }
                            self.speak("Redirecting to Presentation Builder...")
                        else:
                            self.generate_ppt_from_google()
                        return False
                    elif cmd_name == "write_code":
                        prompt = params.get("prompt", "").strip()
                        lang = params.get("language", "python").strip().lower()
                        if type_mode and prompt:
                            self.redirect_info = {
                                "action": "redirect_code_assistant",
                                "prompt": prompt,
                                "language": lang
                            }
                            self.speak("Redirecting to Code Assistant...")
                        else:
                            self.speak("Code generation requested. Please use the Code Assistant panel for code writing.")
                        return False
                    elif cmd_name == "email_assistant":
                        to = params.get("to", "").strip()
                        purpose = params.get("purpose", "").strip()
                        if type_mode:
                            self.redirect_info = {
                                "action": "redirect_email_assistant",
                                "to": to,
                                "purpose": purpose
                            }
                            self.speak("Redirecting to Email Assistant...")
                        else:
                            self.speak("Please use the dashboard email assistant to draft your email.")
                        return False
                    elif cmd_name == "wifi_password":
                        self.get_wifi_password()
                        return False
                    elif cmd_name == "play_music":
                        song = params.get("song_name", "").strip()
                        if song:
                            self.play_song(song)
                        else:
                            self.play_music()
                        return False
                    elif cmd_name == "pause_music":
                        self.pause_music()
                        return False
                    elif cmd_name == "stop_music":
                        self.stop_music()
                        return False
                    elif cmd_name == "next_song":
                        self.next_song()
                        return False
                    elif cmd_name == "previous_song":
                        self.previous_song()
                        return False
                    elif cmd_name == "volume_up":
                        self.volume_up()
                        return False
                    elif cmd_name == "volume_down":
                        self.volume_down()
                        return False
                    elif cmd_name == "toggle_mute":
                        self.toggle_mute()
                        return False
                    elif cmd_name == "storage_info":
                        self.get_storage_info()
                        return False

            # 2. Local Fallback (if LLM routing fails or times out)
            # Process other system commands locally
            print("LLM intent routing failed or skipped. Falling back to keyword matching...")
            if "diagnostics" in cmd_lower or "systems check" in cmd_lower or "diagnose" in cmd_lower:
                self.run_diagnostics()
            elif "system" in cmd_lower:
                self.system_info()
            elif "screenshot" in cmd_lower:
                self.take_screenshot()
            elif self.execute_action_command(command):
                return False
            elif "open" in cmd_lower:
                app = re.sub(r'(?i)\bopen\b', '', command).strip()
                self.smart_open_application(app)
            elif "close" in cmd_lower:
                app = re.sub(r'(?i)\bclose\b', '', command).strip()
                self.smart_close_application(app)
            elif any(x in cmd_lower for x in ["automation mode", "web automation", "screen automation", "start automation"]):
                self.automation_mode()
            elif "search" in cmd_lower and "wikipedia" not in cmd_lower:
                query = re.sub(r'(?i)\bsearch\b', '', command).strip()
                self.search_google(query)
            elif "search wikipedia" in cmd_lower:
                query = re.sub(r'(?i)\bsearch wikipedia\b', '', command).strip()
                try:
                    results = wikipedia.summary(query, sentences=2)
                    self.speak(f"According to Wikipedia: {results}")
                except Exception as e:
                    self.speak(f"Error searching Wikipedia: {str(e)}")
            elif cmd_lower in ["shutdown", "shutdown pc", "shutdown computer", "turn off pc", "power off pc"]:
                self.shutdown_pc()
            elif cmd_lower in ["restart", "restart pc", "restart computer", "reboot", "reboot pc", "reboot computer"]:
                self.restart_pc()
            elif cmd_lower in ["lock", "lock pc", "lock computer", "lock screen"]:
                self.lock_pc()
            elif "wikipedia" in cmd_lower:
                query = re.sub(r'(?i)\bwikipedia\b', '', command).strip()
                self.wikipedia_search(query)
            elif "typing speed" in cmd_lower:
                speed = re.sub(r'(?i)\btyping speed\b', '', command).strip()
                self.set_typing_speed(speed)
            elif "live weather" in cmd_lower:
                self.get_live_weather()
            elif "weather" in cmd_lower:
                if "weather in" in cmd_lower:
                    city = re.sub(r'(?i)\bweather in\b', '', command).strip()
                    self.get_weather(city, type_mode)
                elif "weather of" in cmd_lower:
                    city = re.sub(r'(?i)\bweather of\b', '', command).strip()
                    self.get_weather(city, type_mode)
                else:
                    self.get_weather(type_mode=type_mode)
            elif "news" in cmd_lower:
                self.get_news()
            elif "speed test" in cmd_lower:
                self.speed_test()
            elif "stop motion" in cmd_lower or "stop tracking" in cmd_lower or "stop track motion" in cmd_lower:
                if self.motion_tracking_active:
                    self.toggle_motion_tracking()
                else:
                    self.speak("Motion tracking is not active")
            elif "track motion" in cmd_lower:
                if not self.motion_tracking_active:
                    self.toggle_motion_tracking()
                else:
                    self.speak("Motion tracking is already active")
            elif "qr code" in cmd_lower or "generate qr" in cmd_lower:
                self.generate_qr()
            elif any(x in cmd_lower for x in ["generate ppt", "create presentation", "make slides", "make ppt"]):
                self.generate_ppt_from_google()
            elif "play music" in cmd_lower:
                self.play_music()
            elif "volume up" in cmd_lower:
                self.volume_up()
            elif "volume down" in cmd_lower:
                self.volume_down()
            elif any(x in cmd_lower for x in ["mute", "unmute"]):
                self.toggle_mute()
            elif "pause music" in cmd_lower:
                self.pause_music()
            elif "next song" in cmd_lower:
                self.next_song()
            elif "previous song" in cmd_lower:
                self.previous_song()
            elif "stop music" in cmd_lower:
                self.stop_music()
            elif "storage info" in cmd_lower:
                self.get_storage_info()
            elif cmd_lower.strip() == "chat":
                self.chat_with_ai()
            elif "play" in cmd_lower and "song" in cmd_lower:
                song = re.sub(r'(?i)\bplay song\b', '', command).strip()
                self.play_song(song)
            elif "search" in cmd_lower and "youtube" in cmd_lower:
                import urllib.parse
                query = re.sub(r'(?i)\bsearch youtube\b', '', command).strip()
                self.speak(f"Searching YouTube for {query}")
                webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
            elif "send email" in cmd_lower:
                self.speak("Email sending is no longer supported. Please use the Email Assistant to draft and copy your email.")
            elif any(cmd in cmd_lower for cmd in ["wifi password", "wifi", "password"]):
                self.get_wifi_password()
            else:
                try:
                    response = self.get_ai_response(command, "gemini")
                    if response and response.get("text"):
                        self.speak(response["text"])
                    else:
                        self.speak("Command not recognized")
                except Exception:
                    self.speak("Command not recognized")
        except Exception as e:
            self.speak(f"Error processing command: {str(e)}")
        return False  # Signal to continue the program

    def calculate(self, expression=None, type_mode=False):
        """Perform basic arithmetic calculations"""
        try:
            if not expression:
                expression = self.listen_or_type("What calculation would you like me to perform?", type_mode)

            if expression == "none":
                self.speak("Sorry, I couldn't understand the calculation")
                return

            # Clean up the expression
            expression = expression.lower()
            # Replace words with operators
            expression = expression.replace('x', '*')
            expression = expression.replace('multiplied by', '*')
            expression = expression.replace('times', '*')
            expression = expression.replace('divided by', '/')
            expression = expression.replace('divided', '/')
            expression = expression.replace('divide', '/')
            expression = expression.replace('plus', '+')
            expression = expression.replace('minus', '-')
            expression = expression.replace('power', '**')
            
            # Remove any extra spaces
            expression = ' '.join(expression.split())
            
            # Allow digits, operators, decimal points, and spaces
            expression = ''.join(c for c in expression if c.isdigit() or c in '+-*/.() ')
            
            if not expression:
                self.speak("Invalid calculation expression")
                return

            # Safely evaluate mathematical expressions using AST
            def _eval_node(node):
                import ast
                import operator
                safe_ops = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Pow: operator.pow,
                    ast.USub: operator.neg,
                    ast.UAdd: operator.pos,
                }
                if isinstance(node, ast.Expression):
                    return _eval_node(node.body)
                elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return node.value
                elif hasattr(ast, 'Num') and isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    left = _eval_node(node.left)
                    right = _eval_node(node.right)
                    op_type = type(node.op)
                    if op_type in safe_ops:
                        if op_type is ast.Div and right == 0:
                            raise ZeroDivisionError("division by zero")
                        return safe_ops[op_type](left, right)
                    raise ValueError(f"Unsupported operator: {op_type}")
                elif isinstance(node, ast.UnaryOp):
                    operand = _eval_node(node.operand)
                    op_type = type(node.op)
                    if op_type in safe_ops:
                        return safe_ops[op_type](operand)
                    raise ValueError(f"Unsupported unary operator: {op_type}")
                else:
                    raise TypeError(f"Unsupported syntax: {type(node)}")

            import ast
            parsed_tree = ast.parse(expression, mode='eval')
            result = _eval_node(parsed_tree)
            
            # Format the result
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 2)
            
            self.speak(f"The answer is {result}")
            
        except Exception as e:
            self.speak(f"Sorry, I couldn't perform that calculation. Please try again with simple arithmetic operations.")

    def generate_code(self, type_mode=False):
        """Generate code based on user prompt and save to file"""
        try:
            language = self.listen_or_type("Which programming language would you like to use?", type_mode)
            
            if language == "none":
                self.speak("I couldn't understand the programming language")
                return
            
            language_map = {
                'python': ('.py', 'Python'),
                'javascript': ('.js', 'JavaScript'),
                'java': ('.java', 'Java'),
                'c++': ('.cpp', 'C++'),
                'cpp': ('.cpp', 'C++'),
                'c sharp': ('.cs', 'C#'),
                'csharp': ('.cs', 'C#'),
                'react': ('.tsx', 'React'),
                'html': ('.html', 'HTML'),
                'css': ('.css', 'CSS'),
                'php': ('.php', 'PHP'),
                'ruby': ('.rb', 'Ruby'),
                'swift': ('.swift', 'Swift'),
                'kotlin': ('.kt', 'Kotlin'),
                'rust': ('.rs', 'Rust'),
                'typescript': ('.ts', 'TypeScript')
            }
            
            language_lower = language.lower().replace(" ", "")
            if language_lower not in language_map:
                self.speak(f"Sorry, I don't support {language} yet")
                return

            file_extension, formal_language = language_map[language_lower]
            
            prompt = self.listen_or_type(f"What {formal_language} code would you like me to generate?", type_mode)
            
            if prompt == "none":
                self.speak("I couldn't understand your request")
                return
                
            # Use prompt text to generate filename
            sanitized_prompt = ''.join(c for c in prompt.lower() if c.isalnum() or c.isspace())
            filename = f"{sanitized_prompt.replace(' ', '_')}{file_extension}"
            
            code_prompt = f"""Generate {formal_language} code for: {prompt}
            Requirements:
            - Only provide the code, no explanations
            - Make sure the code is complete and runnable
            - Include necessary imports/dependencies
            - Use {formal_language} best practices and conventions
            - Add basic error handling where appropriate
            - Add comments to explain complex logic
            """
            
            try:
                generated_code = code_assistant.generate_code_llama(prompt, formal_language, is_api_call=False)
                
                code_dir = "generated_code"
                if not os.path.exists(code_dir):
                    os.makedirs(code_dir)
                
                filepath = os.path.join(code_dir, filename)
                
                # If file exists, add a number to filename
                counter = 1
                base_filename = filename[:-len(file_extension)]
                while os.path.exists(filepath):
                    filename = f"{base_filename}_{counter}{file_extension}"
                    filepath = os.path.join(code_dir, filename)
                    counter += 1
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(generated_code)
                
                self.speak(f"I've generated the {formal_language} code and saved it as {filename}")
                
            except Exception as e:
                self.speak(f"Error generating code: {str(e)}")
                
        except Exception as e:
            self.speak(f"Error in code generation process: {str(e)}")

    def query_groq(self, question: str) -> str:
        """Helper to query NVIDIA NIM meta/llama-3.3-70b-instruct model (Nemotron Ultra)"""
        try:
            system_prompt = "You are J.A.R.V.I.S., a helpful AI assistant. Provide responses in clear, readable plain text. Never use markdown formatting, bolding, italics, or asterisks (such as **text** or *text*). Keep answers well-structured using normal spacing and punctuation."
            
            # Construct messages using history
            history_msgs = self.chat_history.copy()
            # If the current question is not yet in history (or is different), append it
            if history_msgs and history_msgs[-1].get("content") == question:
                history_msgs.pop()
                
            content = ProviderManager.nvidia_instruct(
                system_prompt=system_prompt,
                messages_history=history_msgs,
                user_prompt=question
            )
            # Strip all asterisks (markdown bold/italic tags) for clean text
            return content.replace("*", "")
        except Exception as e:
            return f"Error with NVIDIA NIM: {str(e)}"

    def get_ai_response(self, question, model_name, timeout=30):
        """Get response from AI model (Now routed to Groq for general/Gemini requests)"""
        try:
            response_text = self.query_groq(question)
            return {
                "text": response_text,
                "model": "groq",
                "confidence": 0.9 if len(response_text) > 100 else 0.7
            }
        except Exception as e:
            print(f"Error with Groq: {str(e)}")
            return None

    def select_best_response(self, responses):
        """Select the best response based on various criteria"""
        valid_responses = [r for r in responses if r is not None]
        
        if not valid_responses:
            return "I apologize, but I couldn't get a valid response from any AI model."
            
        scored_responses = []
        for response in valid_responses:
            score = response["confidence"]
            
            length = len(response["text"])
            if 100 <= length <= 500:
                score += 0.1
            elif length > 500:
                score += 0.05
                
            if response["text"].strip().endswith((".", "!", "?")):
                score += 0.05
                
            scored_responses.append((score, response))
            
        best_response = max(scored_responses, key=lambda x: x[0])[1]
        return f"{best_response['text']}\n(Response provided by {best_response['model'].title()})"

    def chat_with_ai(self):
        """Chat with Gemini AI in a dedicated chat mode"""
        self.speak("Entering chat mode.")
        
        # Determine initial mode based on how chat was activated
        type_mode = False
        if hasattr(self, 'typing_active') and self.typing_active:
            type_mode = True
            print("Assistant: Chat mode activated in type mode.")
        else:
            self.speak("Chat mode activated in voice mode. Say 'type mode' to switch to typed commands.")
        
        while True:
            if type_mode:
                question = self.take_typed_command()
                if question == "voice mode":
                    type_mode = False
                    self.speak("Switching to voice mode. Say your questions or say 'type mode' to switch back to typed commands.")
                    continue
            else:
                question = self.listen()
                if question == "type mode":
                    type_mode = True
                    print("Assistant: Switched to type mode.")
                    continue
            
            if question == "none":
                continue
                
            if "exit chat" in question.lower():
                self.speak("Exiting chat mode")
                break
            
            if not type_mode:
                self.speak("Let me think about that...")
            
            try:
                response = self.get_ai_response(question, "gemini")
                if response:
                    if type_mode:
                        print(f"Assistant: {response['text']}")
                    else:
                        self.speak(response["text"])
                else:
                    if type_mode:
                        print("Assistant: I apologize, but I couldn't get a valid response.")
                    else:
                        self.speak("I apologize, but I couldn't get a valid response.")
            except Exception as e:
                if type_mode:
                    print(f"Assistant: Error: {str(e)}")
                else:
                    self.speak(f"Error: {str(e)}")

    @auto_retry(max_attempts=3)
    def get_live_weather(self):
        """Get weather information for user's current location"""
        try:
            location_url = f"https://ipapi.co/json/"
            location_response = requests.get(location_url, timeout=10)
            
            if location_response.status_code == 200:
                location_data = location_response.json()
                city = location_data.get('city')
                
                if not city:
                    self.speak("Could not determine your current location")
                    return
                
                weather_api_key = self.config.get('weather_api_key')
                if not weather_api_key:
                    self.speak("Weather API key not found in config file")
                    return

                weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric"
                weather_response = requests.get(weather_url, timeout=10)

                if weather_response.status_code == 200:
                    weather_data = weather_response.json()
                    temp = weather_data['main']['temp']
                    humidity = weather_data['main']['humidity']
                    desc = weather_data['weather'][0]['description']
                    feels_like = weather_data['main']['feels_like']
                    wind_speed = weather_data['wind']['speed']

                    weather_info = f"Current weather in your location ({city}):\n"
                    weather_info += f"Temperature: {temp}Â°C (Feels like {feels_like}Â°C)\n"
                    weather_info += f"Humidity: {humidity}%\n"
                    weather_info += f"Conditions: {desc}\n"
                    weather_info += f"Wind Speed: {wind_speed} m/s"

                    print(weather_info)
                    self.speak(weather_info)
                else:
                    self.speak(f"Could not fetch weather data for {city}")
            else:
                self.speak("Could not determine your location")

        except Exception as e:
            self.speak(f"Error getting live weather: {str(e)}")

    def process_command(self, command):
        """Process user command"""
        return self.process_command_with_mode(command, False)

    def wish_me(self):
        """Greet user based on time of day"""
        hour = int(datetime.datetime.now().hour)
        if hour >= 0 and hour < 12:
            self.speak("Good Morning sir!")
        elif hour >= 12 and hour < 18:
            self.speak("Good Afternoon sir!")
        else:
            self.speak("Good Evening sir!")
        self.speak("I am Jarvis, your AI assistant. How can I help you?")

    def exit_greeting(self):
        """Farewell message based on time"""
        hour = int(datetime.datetime.now().hour)
        if hour >= 20 or hour < 4:
            self.speak("Bye Bye! Good night sir!")
        else:
            self.speak("Have a good day sir!")

    def play_music(self):
        """Play music from music directory"""
        try:
            songs = os.listdir(self.music_dir)
            if songs:
                self.speak("Playing music")
                os.startfile(os.path.join(self.music_dir, songs[0]))
            else:
                self.speak("No music files found")
        except Exception as e:
            self.speak(f"Error playing music: {str(e)}")

    def volume_up(self):
        """Increase system volume"""
        self.speak("Increasing volume")
        pyautogui.press('volumeup')

    def volume_down(self):
        """Decrease system volume"""
        self.speak("Decreasing volume")
        pyautogui.press('volumedown')

    def toggle_mute(self):
        """Toggle mute/unmute"""
        self.speak("Toggling mute")
        pyautogui.press('volumemute')

    def pause_music(self):
        """Play/Pause music"""
        self.speak("Toggling music playback")
        pyautogui.press('playpause')

    def next_song(self):
        """Play next song"""
        self.speak("Next song")
        pyautogui.press('nexttrack')

    def previous_song(self):
        """Play previous song"""
        self.speak("Previous song")
        pyautogui.press('prevtrack')

    def stop_music(self):
        """Stop music playback"""
        self.speak("Stopping music")
        pyautogui.press('playpause')

    def ask_gemini(self):
        """Nova AI (Groq-powered)"""
        self.speak("What would you like to Nova?")
        question = self.listen()
        if question != "none":
            try:
                response_text = self.query_groq(question)
                self.speak(response_text)
            except Exception as e:
                self.speak(f"Error with Nova (Groq): {str(e)}")

    def automation_mode(self):
        """Interactive web and screen automation mode"""
        try:
            self.speak("Automation mode activated. Say commands like click, scroll, type, press, open url, or say stop automation.")
            while True:
                cmd = self.listen()
                if cmd == "none":
                    continue
                if any(x in cmd.lower() for x in ["stop automation", "exit automation", "quit automation"]):
                    self.speak("Automation mode stopped")
                    break
                done = self.execute_action_command(cmd)
                if not done:
                    self.speak("Action not recognized")
        except Exception as e:
            self.speak(f"Error in automation mode: {str(e)}")

    def _parse_ints(self, text):
        """Parse integers from text"""
        try:
            return [int(x) for x in re.findall(r"-?\d+", text)]
        except Exception:
            return []

    def _press_keys(self, phrase):
        """Press keys or hotkeys from phrase"""
        try:
            keys = []
            tokens = re.split(r"\s+", phrase.strip().lower())
            for t in tokens:
                if t in ["ctrl", "control"]:
                    keys.append("ctrl")
                elif t in ["shift"]:
                    keys.append("shift")
                elif t in ["alt"]:
                    keys.append("alt")
                elif t in ["win", "windows"]:
                    keys.append("win")
                elif t in ["enter", "return"]:
                    keys.append("enter")
                elif t in ["tab"]:
                    keys.append("tab")
                elif t in ["esc", "escape"]:
                    keys.append("esc")
                elif t in ["space", "spacebar"]:
                    keys.append("space")
                elif re.fullmatch(r"f\d{1,2}", t):
                    keys.append(t)
                elif t in ["up", "down", "left", "right"]:
                    keys.append(t)
                else:
                    if len(t) == 1:
                        keys.append(t)
            if not keys:
                return False
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            return True
        except Exception:
            return False

    def execute_action_command(self, command):
        """Execute parsed automation actions"""
        try:
            c = command.strip().lower()
            if c.startswith("click ") and not any(ch.isdigit() for ch in c):
                target = command.split(" ", 1)[1].strip()
                return self.click_by_text(target)
            if c.startswith("open ") and (".com" in c or ".org" in c or ".net" in c or c.startswith("open http")):
                url = c.replace("open ", "").strip()
                if not url.startswith("http"):
                    url = f"https://{url}"
                webbrowser.open(url)
                self.speak("Opened")
                return True

            if c.startswith("type into "):
                parts = command.split(" ", 2)
                if len(parts) >= 3:
                    field = parts[1]
                    text = parts[2]
                    if self.ui_type_into(field, text):
                        return True
                return False

            if c.startswith("scroll") or "scroll" in c:
                nums = self._parse_ints(c)
                amount = nums[0] if nums else 800
                if "up" in c:
                    pyautogui.scroll(amount)
                else:
                    pyautogui.scroll(-abs(amount))
                return True

            if c.startswith("move to") or c.startswith("mouse to"):
                nums = self._parse_ints(c)
                if len(nums) >= 2:
                    pyautogui.moveTo(nums[0], nums[1])
                    return True
                return False

            if c.startswith("click") or c.startswith("double click") or c.startswith("right click"):
                double = c.startswith("double click")
                right = c.startswith("right click")
                if any(x in c for x in ["center", "middle"]):
                    w, h = pyautogui.size()
                    pyautogui.moveTo(w//2, h//2)
                elif any(x in c for x in ["top left", "topleft"]):
                    pyautogui.moveTo(5, 5)
                elif any(x in c for x in ["top right", "topright"]):
                    w, _ = pyautogui.size()
                    pyautogui.moveTo(w-5, 5)
                elif any(x in c for x in ["bottom left", "bottomleft"]):
                    _, h = pyautogui.size()
                    pyautogui.moveTo(5, h-5)
                elif any(x in c for x in ["bottom right", "bottomright"]):
                    w, h = pyautogui.size()
                    pyautogui.moveTo(w-5, h-5)
                else:
                    nums = self._parse_ints(c)
                    if len(nums) >= 2:
                        pyautogui.moveTo(nums[0], nums[1])
                if right:
                    pyautogui.click(button='right')
                elif double:
                    pyautogui.doubleClick()
                else:
                    pyautogui.click()
                return True

            if c.startswith("type ") or c.startswith("write "):
                text = command.split(" ", 1)[1]
                pyautogui.typewrite(text, interval=self.typing_speed)
                return True

            if c.startswith("press "):
                phrase = c.replace("press ", "").strip()
                return self._press_keys(phrase)

            if c in ["new tab", "open new tab"]:
                pyautogui.hotkey('ctrl', 't')
                return True

            if c in ["close tab", "close current tab"]:
                return self.close_current_tab()

            if c in ["next tab", "switch tab"]:
                pyautogui.hotkey('ctrl', 'tab')
                return True

            if c in ["previous tab", "prev tab"]:
                pyautogui.hotkey('ctrl', 'shift', 'tab')
                return True

            if c.startswith("tab "):
                nums = self._parse_ints(c)
                if nums:
                    num = max(1, min(8, nums[0]))
                    pyautogui.hotkey('ctrl', str(num))
                    return True
                return False

            if c in ["back", "go back"]:
                pyautogui.hotkey('alt', 'left')
                return True

            if c in ["forward", "go forward"]:
                pyautogui.hotkey('alt', 'right')
                return True

            if c in ["refresh", "reload"]:
                pyautogui.hotkey('ctrl', 'r')
                return True

            if c.startswith("find ") or "find on page" in c:
                term = c.replace("find on page", "").replace("find", "").strip()
                if term:
                    pyautogui.hotkey('ctrl', 'f')
                    pyautogui.typewrite(term, interval=0.03)
                    pyautogui.press('enter')
                    return True
                return False

            if any(w in c for w in ["back", "rewind", "skip", "forward"]) and any(u in c for u in ["second", "sec", "s", "minute", "min", "m"]):
                sign = -1 if any(w in c for w in ["back", "rewind"]) else 1
                nums = self._parse_ints(c)
                if not nums:
                    return False
                amount = nums[0]
                seconds = amount
                if any(u in c for u in ["minute", "min", "m"]):
                    seconds = amount * 60
                return self.youtube_seek(sign * seconds)

            if c in ["zoom in", "increase zoom"]:
                pyautogui.hotkey('ctrl', '+')
                return True

            if c in ["zoom out", "decrease zoom"]:
                pyautogui.hotkey('ctrl', '-')
                return True

            if c in ["reset zoom", "actual size"]:
                pyautogui.hotkey('ctrl', '0')
                return True

            return False
        except Exception:
            return False

    def click_by_text(self, text):
        """Click on element by name using unified PerceptionEngine, UI Automation, and OCR with verified coordinate conversion."""
        try:
            t = text.strip()
            if not t:
                return False

            # 1. UI Automation direct click
            if self.ui_available:
                if self._ui_click_control_by_name(t):
                    return True

            # 2. Perception Engine sweep (UI + OCR in screen coordinate space)
            obs = ObservationEngine.observe(capture_images=True)
            perception = PerceptionEngine.perceive(
                ui_available=self.ui_available,
                ocr_available=self.ocr_available,
                observation=obs,
                image_path=obs.active_window_screenshot_path or "active_window.png"
            )

            matched_target = perception.find_target(t)
            if matched_target and matched_target.bounds:
                center = matched_target.bounds.center
                pyautogui.moveTo(center.x, center.y)
                pyautogui.click()
                return True

            # 3. Fallback search on page
            if any(k in t.lower() for k in ["tab", "button", "link", "menu", "item"]) or len(t.split()) >= 1:
                pyautogui.hotkey('ctrl', 'f')
                pyautogui.typewrite(t, interval=0.03)
                pyautogui.press('enter')
                time.sleep(0.2)
                return True

            return False
        except Exception as e:
            print(f"[click_by_text Error] {e}")
            return False

    def _ui_click_control_by_name(self, name):
        """Use Windows UI Automation to click a control by its Name"""
        try:
            ctrl = UIAutomationService.find_control_by_name(name, self.ui_available, self._ui)
            if ctrl:
                try:
                    ctrl.Click()
                    return True
                except Exception:
                    try:
                        ctrl.SetFocus()
                        x, y = ctrl.BoundingRectangle.left + ctrl.BoundingRectangle.width // 2, ctrl.BoundingRectangle.top + ctrl.BoundingRectangle.height // 2
                        pyautogui.moveTo(x, y)
                        pyautogui.click()
                        return True
                    except Exception:
                        pass
            return False
        except Exception:
            return False

    def ui_type_into(self, field_name, text):
        """Type into an Edit control by name using UI Automation.
        Delegates control lookup to UIAutomationService for architectural consistency.
        """
        try:
            # Reuse UIAutomationService to find the edit field (prefers EditControl)
            ctrl = UIAutomationService.find_control_by_name(field_name, self.ui_available, self._ui)
            if ctrl:
                try:
                    ctrl.Click()
                    pyautogui.typewrite(text, interval=self.typing_speed)
                    return True
                except Exception:
                    return False
            return False
        except Exception:
            return False

    def listen_or_type(self, prompt_text, type_mode=False):
        """Unified input method: uses keyboard input when in type_mode, voice otherwise."""
        if type_mode:
            print(f"Assistant: {prompt_text}")
            try:
                return input().strip() or "none"
            except Exception:
                return "none"
        else:
            self.speak(prompt_text)
            return self.listen()

    def download_youtube_video(self, query):
        try:
            import youtube_downloader
            youtube_downloader.download_youtube_video(query, self.speak)
        except Exception as e:
            self.speak(f"Error loading youtube downloader: {str(e)}")

    def play_song(self, song_name):
        """Search for and play a specific song from the music directory."""
        try:
            songs = os.listdir(self.music_dir)
            # Case-insensitive substring match
            song_lower = song_name.lower()
            match = next(
                (s for s in songs if song_lower in s.lower()),
                None
            )
            if match:
                self.speak(f"Playing {match}")
                os.startfile(os.path.join(self.music_dir, match))
            else:
                # Fallback: play the first available song
                if songs:
                    self.speak(f"Song '{song_name}' not found. Playing {songs[0]} instead.")
                    os.startfile(os.path.join(self.music_dir, songs[0]))
                else:
                    self.speak("No music files found in the music directory.")
        except Exception as e:
            self.speak(f"Error playing song: {str(e)}")

    def write_email(self):
        """Write an email using Mistral and display it on the terminal"""
        self.speak("What topic should the email be about?")
        topic = self.listen()
        if topic == "none":
            self.speak("Could not understand the topic.")
            return

        self.speak(f"Generating email about '{topic}' using Mistral... Please wait.")
        prompt = f"Write an email about {topic}."

        try:
            res = email_writer.generate_email_mistral(
                prompt_topic=prompt,
                role="Recipient",
                about=topic,
                email_format="Professional",
                sender_details={}
            )
            
            subject = res.get("subject", "Email Draft")
            body = res.get("body", "")

            print("\n--- Draft Email ---")
            print(f"Subject: {subject}\n")
            print(body)
            print("--- End of Draft Email ---\n")

            self.email_content_draft = body
            self.speak("I have drafted the email and displayed it on the terminal. You can review or copy it.")

        except Exception as e:
            self.speak(f"Error generating email: {str(e)}")

    def handle_keyboard(self):
        """Handle keyboard events for pause/resume"""
        import keyboard
    
        def on_space():
            if self.paused:
                self.paused = False
                if self.was_listening:
                    print("Assistant resumed")  # Changed from speak to print
                    self.was_listening = False
    
        keyboard.on_press_key('space', lambda _: on_space())

    def cleanup(self):
        """Clean up resources"""
        try:
            self.speak_queue.put(None)
            if hasattr(self, 'gemini'):
                del self.gemini
            if hasattr(self, 'r'):
                self.r.__exit__(None, None, None)
        except Exception:
            pass

    def run(self):
        """Main run loop"""
        try:
            print("J.A.R.V.I.S. Core Systems Online. Waiting for requests...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down J.A.R.V.I.S. Mainframe...")
        finally:
            self.cleanup()

    def get_wifi_password(self):
        """Get WiFi password for current or specified network"""
        try:
            current_wifi = get_current_wifi()
            if not current_wifi:
                self.speak("You're not connected to any WiFi network")
                return

            try:
                output = subprocess.check_output(
                    ['netsh', 'wlan', 'show', 'profile', 
                     current_wifi, 'key=clear']
                ).decode('utf-8')

                # Extract password
                for line in output.split('\n'):
                    if "Key Content" in line:
                        password = line.split(":")[1].strip()
                        self.speak(f"The password for {current_wifi} is: {password}")
                        print(f"\nNetwork: {current_wifi}")
                        print(f"Password: {password}")
                        return

                self.speak("Could not find password for this network")

            except subprocess.CalledProcessError:
                self.speak("Error getting WiFi password. Please run as administrator.")
            except Exception as e:
                self.speak(f"Error: {str(e)}")

        except Exception as e:
            self.speak("Error retrieving WiFi information")

    def force_activate_window(self, hwnd):
        """Force activate a window"""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            
            time.sleep(0.5)
            
            x, y, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - x
            height = bottom - y
            pyautogui.moveTo(x + width//2, y + height//2)
            time.sleep(0.2)
            
            return True
        except Exception:
            return False

    def enumerate_windows(self):
        """Enumerate visible top-level windows"""
        windows = []
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(hwnd)
        win32gui.EnumWindows(callback, None)
        return windows

    def _hwnd_process_name(self, hwnd):
        """Get process name for a window"""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            p = psutil.Process(pid)
            return p.name().lower()
        except Exception:
            return ""

    def _is_browser_process(self, name):
        """Check if process name is a browser"""
        browsers = {"chrome.exe", "msedge.exe", "brave.exe", "firefox.exe", "opera.exe"}
        return name in browsers

    def close_current_tab(self):
        """Close current tab of active browser window"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            pname = self._hwnd_process_name(hwnd)
            if self._is_browser_process(pname):
                pyautogui.hotkey('ctrl', 'w')
                return True
            for w in self.enumerate_windows():
                pn = self._hwnd_process_name(w)
                if self._is_browser_process(pn):
                    if self.force_activate_window(w):
                        pyautogui.hotkey('ctrl', 'w')
                        return True
            return False
        except Exception:
            return False

    def close_tab_by_name(self, tab_name):
        """Close a browser tab by matching window title"""
        try:
            q = tab_name.strip().lower()
            q = q.replace('.com', '').replace('.org', '').replace('.net', '')
            for w in self.enumerate_windows():
                title = win32gui.GetWindowText(w).lower()
                pn = self._hwnd_process_name(w)
                if self._is_browser_process(pn) and q in title:
                    if self.force_activate_window(w):
                        pyautogui.hotkey('ctrl', 'w')
                        return True
            return False
        except Exception:
            return False

    def find_youtube_window(self):
        """Find a YouTube browser window"""
        try:
            for w in self.enumerate_windows():
                title = win32gui.GetWindowText(w).lower()
                pn = self._hwnd_process_name(w)
                if self._is_browser_process(pn) and "youtube" in title:
                    return w
            return None
        except Exception:
            return None

    def youtube_seek(self, seconds):
        """Seek YouTube by seconds using keyboard shortcuts"""
        try:
            hwnd = self.find_youtube_window()
            if not hwnd:
                self.speak("No YouTube tab found")
                return False
            self.force_activate_window(hwnd)
            time.sleep(0.1)
            step = 10
            key_forward = 'l'
            key_back = 'j'
            total = abs(int(seconds))
            dir_key = key_forward if seconds > 0 else key_back
            steps = total // step
            remainder = total % step
            for _ in range(steps):
                pyautogui.press(dir_key)
                time.sleep(0.05)
            if remainder:
                small_key = 'right' if seconds > 0 else 'left'
                small_steps = max(1, remainder // 5)
                for _ in range(small_steps):
                    pyautogui.press(small_key)
                    time.sleep(0.05)
            return True
        except Exception:
            return False

    def find_application_path(self, query):
        """Find application path via registry, start menu, PATH, and common dirs"""
        try:
            q = query.strip()
            candidates = []

            def read_app_paths(view_flag):
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths", 0, winreg.KEY_READ | view_flag)
                except Exception:
                    return
                i = 0
                while True:
                    try:
                        subname = winreg.EnumKey(key, i)
                        i += 1
                        if q.lower() in subname.lower():
                            try:
                                sk = winreg.OpenKey(key, subname)
                                val, _ = winreg.QueryValueEx(sk, None)
                                if val:
                                    candidates.append(val)
                            except Exception:
                                pass
                    except OSError:
                        break
                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

            read_app_paths(winreg.KEY_WOW64_64KEY)
            read_app_paths(winreg.KEY_WOW64_32KEY)

            if not candidates:
                try:
                    r = subprocess.run(["where", q], capture_output=True, text=True)
                    if r.returncode == 0:
                        for line in r.stdout.splitlines():
                            if line.lower().endswith('.exe') and os.path.exists(line):
                                candidates.append(line)
                                break
                except Exception:
                    pass

            if not candidates:
                start_paths = []
                pd = os.environ.get('ProgramData')
                if pd:
                    start_paths.append(os.path.join(pd, 'Microsoft', 'Windows', 'Start Menu', 'Programs'))
                appd = os.environ.get('APPDATA')
                if appd:
                    start_paths.append(os.path.join(appd, 'Microsoft', 'Windows', 'Start Menu', 'Programs'))
                for sp in start_paths:
                    if os.path.isdir(sp):
                        for root, _, files in os.walk(sp):
                            for f in files:
                                if q.lower() in f.lower() and (f.lower().endswith('.lnk') or f.lower().endswith('.url') or f.lower().endswith('.exe')):
                                    candidates.append(os.path.join(root, f))
                                    break
                            if candidates:
                                break
                    if candidates:
                        break

            if not candidates:
                for base in [r"C:\\Program Files", r"C:\\Program Files (x86)"]:
                    if os.path.isdir(base):
                        for root, dirs, files in os.walk(base):
                            for f in files:
                                if q.lower() in f.lower() and f.lower().endswith('.exe'):
                                    candidates.append(os.path.join(root, f))
                                    break
                            if candidates:
                                break
                        if candidates:
                            break

            return candidates[0] if candidates else None
        except Exception:
            return None

    def write_text_to_focused_app(self, app_name, text):
        """Types or pastes text into the currently active/focused window after a short delay"""
        try:
            import time
            import pyperclip
            import pyautogui
            import pygetwindow as gw
            import win32gui
            import win32con
            import win32process
            import win32api
            import win32com.client
            
            # Map common synonyms to window titles
            title_synonyms = {
                "notepad": ["notepad"],
                "word": ["word", "winword"],
                "winword": ["word", "winword"],
                "excel": ["excel"],
                "powerpoint": ["powerpoint", "powerpnt"],
                "powerpnt": ["powerpoint", "powerpnt"],
                "chrome": ["chrome", "google chrome"],
                "brave": ["brave"],
                "edge": ["edge", "msedge"],
                "firefox": ["firefox"]
            }
            
            search_terms = title_synonyms.get(app_name.lower(), [app_name.lower()])
            
            # Try to find and focus the window in a loop for up to 5 seconds
            start_time = time.time()
            focused = False
            
            while time.time() - start_time < 5.0:
                all_windows = gw.getAllWindows()
                target_win = None
                for w in all_windows:
                    if w.title and any(term in w.title.lower() for term in search_terms):
                        # Ensure we only match visible windows to avoid background processes
                        if win32gui.IsWindowVisible(w._hWnd):
                            target_win = w
                            break
                
                if target_win:
                    hwnd = target_win._hWnd
                    print(f"[System: Found window to focus: '{target_win.title}' (HWND: {hwnd})]")
                    
                    try:
                        # Restore if minimized
                        if win32gui.IsIconic(hwnd):
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            time.sleep(0.2)
                        
                        # --- Thread Input Attachment Hack to force active foreground focus ---
                        fore_hwnd = win32gui.GetForegroundWindow()
                        fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
                        my_thread = win32api.GetCurrentThreadId()
                        
                        attached = False
                        if fore_thread != my_thread:
                            try:
                                win32process.AttachThreadInput(my_thread, fore_thread, True)
                                attached = True
                            except Exception:
                                pass
                        
                        # Bring target window to top and foreground
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.SetActiveWindow(hwnd)
                        win32gui.BringWindowToTop(hwnd)
                        focused = True
                        
                        # Detach input threads
                        if attached:
                            try:
                                win32process.AttachThreadInput(my_thread, fore_thread, False)
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"win32gui focus failed: {str(e)}")
                    
                    # WScript AppActivate as secondary fallback/reinforcement (using exact window title)
                    try:
                        shell = win32com.client.Dispatch("WScript.Shell")
                        if shell.AppActivate(target_win.title):
                            focused = True
                    except Exception as e:
                        print(f"AppActivate fallback failed: {str(e)}")
                    
                    # Click on the title bar of the window to force active OS input focus
                    if focused:
                        try:
                            time.sleep(0.3)
                            x, y, right, bottom = win32gui.GetWindowRect(hwnd)
                            # Safe title bar click: x + 150 (offset to the right) and y + 15 (offset down)
                            pyautogui.click(x + 150, y + 15)
                            time.sleep(0.2)
                        except Exception as e:
                            print(f"Title bar click failed: {str(e)}")
                        break
                        
                time.sleep(0.5)
            
            # Additional safety delay for focus transition
            time.sleep(0.5)
            
            # Copy text to clipboard and simulate Ctrl+V to paste
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            
            print(f"[System: Wrote generated content to focused application '{app_name}']")
        except Exception as e:
            print(f"Error typing text to application: {str(e)}")

    def smart_open_application(self, app_name, write_content=None):
        """Open any application or website with search and feedback"""
        try:
            name = app_name.strip().lower()
            if any(x in name for x in [".com", ".org", ".net"]) or name in ["youtube", "blackbox", "chatgpt", "github", "gemini", "google", "gmail", "maps"]:
                site_map = {
                    "youtube": "https://youtube.com",
                    "blackbox": "https://blackbox.ai",
                    "chatgpt": "https://chat.openai.com",
                    "github": "https://github.com",
                    "gemini": "https://gemini.com",
                    "google": "https://google.com",
                    "gmail": "https://mail.google.com",
                    "maps": "https://maps.google.com"
                }
                url = site_map.get(name)
                if not url and any(x in name for x in [".com", ".org", ".net"]):
                    url = f"https://{name}" if not name.startswith("http") else name
                if url:
                    webbrowser.open(url)
                    self.speak(f"{app_name} opened")
                    if write_content:
                        self.write_text_to_focused_app(app_name, write_content)
                    return

            exe_synonyms = {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "word": "winword.exe",
                "excel": "excel.exe",
                "powerpoint": "powerpnt.exe",
                "chrome": "chrome.exe",
                "brave": "brave.exe",
                "edge": "msedge.exe",
                "firefox": "firefox.exe"
            }
            target = exe_synonyms.get(name, None)
            path = self.find_application_path(target or name)
            if path:
                try:
                    if write_content:
                        try:
                            # 1. Write the document to a local folder in the workspace to bypass UWP sandboxing
                            docs_dir = os.path.abspath("jarvis_documents")
                            if not os.path.exists(docs_dir):
                                os.makedirs(docs_dir)
                            
                            ext = ".txt"
                            if "excel" in name:
                                ext = ".csv"
                            elif "word" in name:
                                ext = ".docx"
                            
                            import uuid
                            temp_file = os.path.join(docs_dir, f"essay_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}")
                            with open(temp_file, "w", encoding="utf-8") as f:
                                f.write(write_content)
                            
                            # 2. Open the file natively using Windows file association (always opens in associated editor)
                            os.startfile(temp_file)
                            self.speak(f"{app_name} opened and text written")
                            return
                        except Exception as e:
                            print(f"[System: File launch fallback triggered: {str(e)}]")
                            # Fallback: standard open + paste
                            os.startfile(path)
                            self.speak(f"{app_name} opened")
                            self.write_text_to_focused_app(app_name, write_content)
                            return
                    else:
                        os.startfile(path)
                        self.speak(f"{app_name} opened")
                        return
                except Exception:
                    try:
                        subprocess.Popen(path)
                        self.speak(f"{app_name} opened")
                        if write_content:
                            self.write_text_to_focused_app(app_name, write_content)
                        return
                    except Exception as e:
                        self.speak(f"Error opening {app_name}: {str(e)}")
                        return
            self.speak(f"There is no {app_name}")
        except Exception as e:
            self.speak(f"Error opening {app_name}: {str(e)}")

    def smart_close_application(self, app_name):
        """Close any application or browser tab with state-aware feedback"""
        try:
            name = app_name.strip().lower()
            if any(x in name for x in ["tab", "current tab"]) or name in ["current", "current tab"]:
                if self.close_current_tab():
                    self.speak("Current tab closed")
                else:
                    self.speak("No browser tab to close")
                return

            site_key = name.replace('.com', '').strip()
            if site_key in ["youtube", "blackbox", "chatgpt", "github", "gemini", "google", "gmail", "maps"]:
                if self.close_tab_by_name(site_key):
                    self.speak(f"{site_key} tab closed")
                else:
                    self.speak(f"No {site_key} tab found")
                return

            exe_synonyms = {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "word": "winword.exe",
                "excel": "excel.exe",
                "powerpoint": "powerpnt.exe",
                "chrome": "chrome.exe",
                "brave": "brave.exe",
                "edge": "msedge.exe",
                "firefox": "firefox.exe"
            }
            target = exe_synonyms.get(name, name if name.endswith('.exe') else None)
            if not target:
                path = self.find_application_path(name)
                if path:
                    target = os.path.basename(path)
            if not target:
                self.speak(f"There is no {app_name}")
                return

            procs = [p for p in psutil.process_iter(['name', 'pid']) if p.info['name'] and p.info['name'].lower() == target.lower()]
            if not procs:
                self.speak(f"{app_name} is already closed")
                return
            try:
                result = subprocess.run(['taskkill', '/F', '/IM', target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    self.speak(f"{app_name} closed")
                else:
                    self.speak(f"Failed to close {app_name}: {result.stderr}")
            except Exception as e:
                self.speak(f"Error closing {app_name}: {str(e)}")
        except Exception as e:
            self.speak(f"Error closing {app_name}: {str(e)}")

    def get_storage_info(self):
        """Get storage information for all drives"""
        try:
            drives = []
            for partition in psutil.disk_partitions():
                if 'fixed' in partition.opts:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    total = round(usage.total / (1024**3), 2)
                    used = round(usage.used / (1024**3), 2)
                    free = round(usage.free / (1024**3), 2)
                    percent = usage.percent
                    
                    drive_info = f"Drive {partition.device.split(':')[0]}:\n"
                    drive_info += f"Total Space: {total} GB\n"
                    drive_info += f"Used Space: {used} GB\n"
                    drive_info += f"Free Space: {free} GB\n"
                    drive_info += f"Usage: {percent}%\n"
                    drives.append(drive_info)
            
            if drives:
                storage_info = "Storage Information:\n" + "\n".join(drives)
                print(storage_info)  
                self.speak("Here's your storage information:")
                for drive in drives:
                    self.speak(drive)
            else:
                self.speak("No storage drives found")
                
        except Exception as e:
            self.speak(f"Error getting storage information: {str(e)}")



if __name__ == "__main__":
    import os as _main_os
    _port = int(_main_os.environ.get("PORT", 5000))
    # Boot assistant in background so Flask can start immediately
    import threading as _threading
    global assistant_ref
    def _start():
        global assistant_ref
        assistant_ref = JarvisAssistant()
    _threading.Thread(target=_start, daemon=True).start()
    app.run(host="0.0.0.0", port=_port, debug=False, threaded=True)