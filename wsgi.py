"""
J.A.R.V.I.S. — Render-compatible WSGI entrypoint
Handles:
  - Windows-only import isolation (pyttsx3, win32*, pyautogui, etc.)
  - Graceful degradation for desktop-only features on Linux
  - Health check + readiness + metrics endpoints
  - Request throttler (soft load balancing on free tier)
  - CORS update for Render domain
  - Gunicorn-ready `application` export
"""

import os
import sys
import logging
import threading

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis.wsgi")

# ── Platform guard: stub out Windows-only modules on Linux ───────────────────
IS_WINDOWS = sys.platform.startswith("win")

if not IS_WINDOWS:
    import types

    _WIN_STUBS = [
        "pyttsx3", "speech_recognition", "pythoncom",
        "pyautogui", "pygetwindow", "pyperclip",
        "pynput", "pynput.keyboard",
        "win32gui", "win32con", "win32api", "win32process", "win32com",
        "win32com.client", "winreg",
        "uiautomation", "keyboard",
        "tkinter", "tkinter.ttk",
        "speedtest",
    ]
    for _mod in _WIN_STUBS:
        if _mod not in sys.modules:
            stub = types.ModuleType(_mod)
            # Provide no-op stubs for the most common sub-attributes
            stub.Controller  = lambda *a, **kw: None
            stub.Tk          = lambda *a, **kw: None
            stub.Style       = lambda *a, **kw: None
            stub.Recognizer  = lambda *a, **kw: None
            sys.modules[_mod] = stub

    os.environ.setdefault("DISPLAY", "")

# ── Load .env (dev) / Render env vars (prod) ─────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Import the main Flask app from buddy.py ───────────────────────────────────
try:
    from buddy import app, JarvisAssistant
    logger.info("buddy.py imported OK.")
except Exception as exc:
    logger.critical("Failed to import buddy.py: %s", exc, exc_info=True)
    raise

# ── Update CORS for Render deployment ────────────────────────────────────────
from flask_cors import CORS

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
_origins = ["http://localhost:5000", "http://127.0.0.1:5000"]
if RENDER_URL:
    _origins += [RENDER_URL, RENDER_URL.replace("http://", "https://")]

CORS(app, origins=_origins, supports_credentials=True)

# ── Attach Health Manager & Request Throttler ─────────────────────────────────
from health_manager import RequestThrottler, HealthMonitor, register_health_routes

throttler = RequestThrottler()
monitor   = HealthMonitor()

throttler.register(app)
monitor.register(app)
register_health_routes(app, throttler, monitor)

logger.info("Health manager & request throttler attached.")

# ── Boot JarvisAssistant in background (keeps Gunicorn bind instant) ──────────
def _boot_assistant():
    try:
        import buddy
        buddy.assistant_ref = JarvisAssistant()
        logger.info("JarvisAssistant initialized and ready.")
    except Exception as exc:
        logger.error("JarvisAssistant init failed (non-fatal): %s", exc, exc_info=True)

_boot_thread = threading.Thread(target=_boot_assistant, daemon=True, name="jarvis-boot")
_boot_thread.start()

# ── Gunicorn entry point ──────────────────────────────────────────────────────
application = app   # gunicorn wsgi:application

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
