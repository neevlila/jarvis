<div align="center">

```
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

### Just A Rather Very Intelligent System

**Autonomous AI Desktop Ecosystem · Agentic Engineering Suite · Multi-Provider Intelligence**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Gunicorn](https://img.shields.io/badge/Gunicorn-22.0+-499848?style=flat&logo=gunicorn&logoColor=white)](https://gunicorn.org/)
[![Render](https://img.shields.io/badge/Hosted_on-Render-46E3B7?style=flat&logo=render&logoColor=white)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-cyan?style=flat)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-98%2B_scenarios-brightgreen?style=flat)](#-testing)

</div>

---

## What is J.A.R.V.I.S.?

**J.A.R.V.I.S.** is a production-grade, full-stack autonomous AI ecosystem that runs as a local Flask server with a **glassmorphic cyber-tactical web interface**. It routes intelligence across **Google Gemini 2.5 Flash**, **Groq LPU** (ultra-low latency), and **NVIDIA NIM** — automatically falling back between providers for 100% resilience.

It is not a single chatbot. It is a **suite of seven specialized AI engines** unified under one interface.

---

## Feature Engines

### 🧠 Idea Engine & Blueprint Synthesizer
Transforms raw technology stacks and problem statements into structured project blueprints.

- **Stack Synergy Analysis** — evaluates cross-technology integration potential
- **6-Factor Weighted Scoring** — Stack Fit (25%) · Feasibility (20%) · Real-World Value (20%) · Technical Depth (15%) · Portfolio Impact (10%) · Novelty (10%)
- **Creative Director** — generates domain-grounded color palettes, typography, motion strategy, and 3D usage rationale
- **Quality Control Gate** — rejects weak ideas, forces deterministic fallback synthesis

### 📐 Master Build Prompt Engine
Converts blueprints into exhaustive **25+ section AI-readable engineering specifications** ready to drop into any AI coding agent.

- **Multi-Platform Output** — Universal Markdown · Antigravity Planning Mode · Cursor Rules (`.cursorrules`) · Claude Code (`CLAUDE.md`) · Lovable · v0 · Bolt.new
- **Real-Time Completeness Telemetry** — continuous scoring across Technical Depth, UX/UI, Visual Direction, and Phased Execution
- **Adapter Layer** — auto-reformats specs per target platform's expected syntax

### 💻 Interactive Code Assistant & Live Compiler
A fully interactive in-browser terminal with real AI debugging.

- **Multi-Language Runner** — Python · JavaScript · TypeScript · C++ · Java · Go · Rust · C#
- **Real-Time SSE Streaming** — character-by-character `stdout`/`stderr` via Server-Sent Events
- **Interactive stdin** — live process input without page refresh
- **One-Click AI Diagnostics** — analyzes runtime stack traces and generates inline drop-in fixes

### 🤖 Intelligence Hub & Autonomous Orchestration
Seven sub-engines coordinated by a master `IntelligenceCoordinator`.

| Sub-Engine | Role |
|---|---|
| `MemoryEngine` | Semantic + episodic long-term memory with relevance decay |
| `GoalEngine` | Recursive hierarchical task decomposition + contradiction detection |
| `SelfCritiqueEngine` | Validates decisions before execution — catches assumptions, contradictions, unsafe ops |
| `RiskSafetyEngine` | Blocks CRITICAL/HIGH risk actions (file deletion, system shutdown, DB drops) |
| `ProjectAnalyzer` | Static security, maintainability, and architectural dependency inspection |
| `SkillEngine` | Plugin/skill registry — modular capability discovery and lifecycle |
| `PerformanceEngine` | Tracks response latency, accuracy, and provider health over time |

### 🔍 SEO Intelligence Engine
Full on-demand SEO auditing pipeline.

- Fetches and parses live URLs with **SSRF protection**
- Deterministic analysis across meta, headings, content, performance signals, structured data, and mobile
- Explainable **category scores** + composite weighted score
- Evidence-grounded AI recommendation layer
- Exports full audit as **Markdown or JSON**

### 🖥️ Closed-Loop Desktop Automation *(Windows)*
8-stage autonomous desktop agent.

```
Observe → Perceive → Build Context → Decide → Critique → Validate → Execute → Verify
```

- **OCR Service** — reads screen text from any region
- **UI Automation Service** — interacts with native Windows controls
- **Session Manager** — tracks multi-step task state and replanning on failure
- **Coordinate Engine** — resolves UI elements across display scales and DPI

### 🌍 Geolocation Intelligence Engine
- Extracts IP entities from natural language queries
- Validates syntax, detects private/reserved ranges
- Multi-provider resolution with normalization
- Dispatches results to the 3D globe interface

---

## Architecture

```
J.A.R.V.I.S/
├── buddy.py                      # Flask REST/SSE API (40+ routes) + JarvisAssistant
├── wsgi.py                       # Render/Gunicorn entrypoint + Windows stub isolation
├── gunicorn.conf.py              # Production WSGI config (threads, timeout, recycling)
├── health_manager.py             # /health · /ready · /metrics + RequestThrottler
├── config.py                     # Centralized env loader + typed config classes
├── requirements.txt              # Python dependencies (Linux-safe)
├── render.yaml                   # Render Blueprint (IaC)
│
├── providers/
│   └── provider_manager.py       # Resilient AI routing: Gemini → Groq → NVIDIA NIM
│
├── idea_engine/                  # Idea Engine & Master Prompt System
│   ├── engine.py                 # Master coordinator
│   ├── generator.py              # Idea generation + deterministic fallback
│   ├── prompt_engine.py          # 25+ section spec synthesizer
│   ├── creative_director.py      # Visual identity & design systems
│   ├── stack_analyzer.py         # Cross-technology synergy analysis
│   ├── quality_control.py        # Idea scoring gate
│   ├── scoring.py                # 6-factor deterministic scorer
│   ├── adapters.py               # Multi-platform output formatters
│   └── models.py                 # Pydantic data models
│
├── intelligence/                 # Agentic Intelligence Hub
│   ├── coordinator.py            # Master orchestrator + trace logging
│   ├── memory_engine.py          # Durable semantic/episodic memory
│   ├── goal_engine.py            # Recursive goal decomposition
│   ├── critique.py               # Self-critique & assumption detection
│   ├── risk_engine.py            # Risk/safety evaluation layer
│   ├── project_analyzer.py       # Codebase health inspector
│   ├── skill_engine.py           # Plugin/skill registry
│   ├── performance.py            # Latency & accuracy tracker
│   └── models.py                 # Shared intelligence models
│
├── seo_engine/                   # SEO Intelligence Engine
│   ├── engine.py                 # Master SEO pipeline
│   ├── fetcher.py                # SSRF-safe URL fetcher
│   ├── analyzer.py               # Deterministic SEO analyzer
│   ├── scoring.py                # Category + composite scorer
│   ├── prioritizer.py            # Action plan generator
│   ├── ai_interpreter.py         # Evidence-grounded AI recommendations
│   └── models.py                 # SEO data models
│
├── desktop_engine/               # Closed-Loop Desktop Automation (Windows)
│   ├── orchestrator.py           # 8-stage agent loop
│   ├── observation_engine.py     # Screen capture & state snapshot
│   ├── perception_engine.py      # UI element detection & classification
│   ├── context_engine.py         # Task context & state tracking
│   ├── decision_engine.py        # LLM-driven action selection
│   ├── action_executor.py        # Mouse, keyboard, app control
│   ├── validation_engine.py      # Pre-execution safety validation
│   ├── verification_engine.py    # Post-execution success verification
│   ├── ocr_service.py            # Text extraction from screen regions
│   ├── ui_automation_service.py  # Native Windows control interaction
│   ├── session_manager.py        # Multi-step task state & replanning
│   ├── coordinates.py            # DPI-aware coordinate resolution
│   └── models.py                 # Desktop engine models
│
├── web/                          # Glassmorphic Cyber-Tactical Interface
│   ├── index.html                # Single-page app + modal viewports
│   ├── app.js                    # Client controller + SSE streams
│   ├── globe.js                  # Interactive 3D geolocation globe
│   ├── style.css                 # Futuristic cyber aesthetic
│   └── maplibre-gl.*             # Map rendering library (bundled)
│
├── geolocation_engine.py         # IP entity extraction + geo resolution
├── code_assistant.py             # Code generation & explanation pipelines
├── email_writer.py               # AI email drafting
├── ppt_generator.py              # Automated PowerPoint generation (Windows)
├── qr.py                         # QR code generator
├── youtube_downloader.py         # YouTube video downloader (yt-dlp)
├── wifi_helper.py                # WiFi SSID & password lookup (Windows)
│
└── tests/                        # 98+ automated test scenarios
```

---

## AI Provider Routing

J.A.R.V.I.S. never depends on a single AI provider. The `ProviderManager` tries each in order:

```
Primary  →  Google Gemini 2.5 Flash   (low latency, multimodal)
Fallback →  Groq LPU                  (ultra-fast inference)
Fallback →  NVIDIA NIM                (Nemotron / Mistral / Gemma)
Fallback →  OpenRouter                (broad model coverage)
```

Connection pooling (`HTTPAdapter`) and response caching are built in.

---

## Quick Start (Local — Windows)

### 1. Clone

```bash
git clone https://github.com/your-username/jarvis.git
cd jarvis
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# LLM
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
NVIDIA_API_KEY=your_nvidia_key
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
OPENROUTER_API_KEY=your_openrouter_key

# Vision & Multimodal
NVIDIA_VISION_API_KEY=your_nvidia_vision_key
NVIDIA_NEMOTRON_API_KEY=your_nemotron_key
NVIDIA_GEMMA_API_KEY=your_gemma_key
NVIDIA_MISTRAL_API_KEY=your_mistral_key

# External APIs
WEATHER_API_KEY=your_openweather_key
NEWS_API_KEY=your_newsapi_key
```

### 4. Launch

```bash
python buddy.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## Deploy to Render (Cloud — Free Tier)

J.A.R.V.I.S. is fully configured for [Render](https://render.com) with zero extra setup.

### 1. Push to GitHub

```bash
git add .
git commit -m "feat: deploy to render"
git push origin main
```

> ⚠️ `.env` is in `.gitignore` — your keys stay local. Add them via the Render Dashboard.

### 2. Create Web Service on Render

- **New** → **Web Service** → connect your repo
- Render auto-detects `render.yaml` → click **Apply Blueprint**
- Or set manually:
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn wsgi:application -c gunicorn.conf.py`
  - **Plan:** Free

### 3. Add Environment Variables

Set all keys from your `.env` in **Dashboard → Environment**.

### Health Endpoints

| Endpoint | Purpose |
|---|---|
| `/health` | Liveness probe — Render pings every 30 s |
| `/ready` | Readiness probe — confirms assistant initialized |
| `/metrics` | Live ops data: request rate, error rate, memory usage |

> **Note:** Desktop-only features (voice, PyAutoGUI, win32, PPT via COM) are automatically disabled on Linux/Render via graceful stubs. All AI, SEO, Idea Engine, and Code Assistant features work fully in the cloud.

---

## API Reference

All endpoints require a valid `jarvis_token` cookie (set automatically on first page load) or `X-JARVIS-Auth` header.

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/status` | System stats: CPU, RAM, drives, notifications |
| `GET` | `/api/context` | Current assistant context snapshot |
| `POST` | `/api/command` | Natural language command dispatcher |
| `POST` | `/api/task` | Desktop automation task (Windows only) |
| `POST` | `/api/vision` | Image understanding / visual reasoning |
| `POST` | `/api/code_assistant` | Code generation (multi-language) |
| `POST` | `/api/run_code` | Live code execution with streaming |
| `GET` | `/api/console_stream` | SSE stream for real-time console output |
| `POST` | `/api/console_input` | Send stdin to running process |
| `POST` | `/api/debug_code` | AI-powered runtime error analysis |
| `POST` | `/api/idea_engine/generate` | Generate project ideas from stack |
| `POST` | `/api/idea_engine/analyze_stack` | Technology stack analysis |
| `POST` | `/api/idea_engine/generate_master_prompt` | Generate 25+ section build spec |
| `POST` | `/api/seo/analyze` | Full SEO audit for a URL |
| `POST` | `/api/seo/analyze_project` | SEO audit for a local HTML project |
| `POST` | `/api/seo/export` | Export audit as Markdown/JSON |
| `POST` | `/api/intelligence/analyze_project` | Codebase health & security scan |
| `POST` | `/api/intelligence/decompose_goal` | Recursive goal decomposition |
| `POST` | `/api/intelligence/critique` | Self-critique a plan or answer |
| `POST` | `/api/intelligence/risk_assess` | Risk/safety evaluation |
| `GET/POST/DELETE` | `/api/intelligence/memory` | Memory store operations |
| `POST` | `/api/geolocation/lookup` | IP geolocation resolution |
| `POST` | `/api/generate_qr` | QR code generation |
| `POST` | `/api/generate_email` | AI email drafting |
| `POST` | `/api/generate_ppt` | PowerPoint generation (Windows) |
| `GET` | `/api/weather` | Current weather data |
| `GET` | `/api/news` | Live news headlines |
| `POST` | `/api/listen_voice` | Voice input capture (Windows) |
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe |
| `GET` | `/metrics` | Operational metrics |

---

## Testing

Run the full suite of 98+ deterministic test scenarios:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Test coverage spans all engines:

```
tests/
├── test_idea_engine.py           # Idea generation pipeline
├── test_idea_scoring.py          # 6-factor scoring engine
├── test_idea_quality_control.py  # QC gate scenarios
├── test_master_prompt_engine.py  # 25+ section spec generation
├── test_stack_analyzer.py        # Stack synergy analysis
├── test_intelligence.py          # Intelligence coordinator
├── test_seo_analyzer.py          # SEO analysis engine
├── test_seo_scoring.py           # SEO scoring
├── test_seo_api.py               # SEO API integration
├── test_seo_fetcher_security.py  # SSRF protection
├── test_orchestrator.py          # Desktop agent loop
├── test_action_executor.py       # Action execution
├── test_decision_engine.py       # LLM decision selection
├── test_observation.py           # Screen observation
├── test_verification.py          # Post-execution verification
├── test_context_engine.py        # Context tracking
├── test_coordinates.py           # Coordinate resolution
├── test_geolocation_engine.py    # Geolocation pipeline
├── test_vision.py                # Vision engine
└── test_qa_master_suite.py       # End-to-end QA master suite
```

---

## Security

| Protection | Implementation |
|---|---|
| **CSRF / Session Auth** | Cryptographically secure `secrets.token_hex(16)` cookie, verified on every API call |
| **CORS** | Strict origin whitelist — only trusted domains allowed |
| **SSRF Protection** | SEO fetcher blocks private IP ranges, localhost, and internal hostnames |
| **Command Injection** | All subprocess calls use list arguments — no shell string execution |
| **Safe Math Eval** | AST-sandboxed expression parser — no `eval()` |
| **Risk Gate** | `RiskSafetyEngine` blocks CRITICAL/HIGH actions before execution |
| **No Secrets in Code** | All keys via `.env` / Render environment variables |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11 · Flask 3.0 · Gunicorn (gthread) |
| **AI Routing** | Google Gemini 2.5 Flash · Groq · NVIDIA NIM · OpenRouter |
| **Frontend** | Vanilla JS · CSS3 (glassmorphism) · Server-Sent Events |
| **3D Visualization** | Three.js · MapLibre GL |
| **Desktop Automation** | PyAutoGUI · pynput · win32api · UIAutomation *(Windows)* |
| **Computer Vision** | OpenCV Headless · NVIDIA Vision API |
| **Cloud Deploy** | Render Free Tier · render.yaml Blueprint |
| **Testing** | Python `unittest` · 98+ scenarios |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ⚡ by a developer who wanted their own J.A.R.V.I.S.

</div>
