# ─────────────────────────────────────────────────────────────
#  Gunicorn Configuration — J.A.R.V.I.S. on Render Free Tier
#  Doc: https://docs.gunicorn.org/en/stable/settings.html
# ─────────────────────────────────────────────────────────────

import os
import multiprocessing

# ── Binding ───────────────────────────────────────────────────
# Render injects PORT automatically; default to 10000 (Render's standard)
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# ── Workers ───────────────────────────────────────────────────
# Free tier = 0.1 vCPU / 512 MB RAM
# Keep workers=1 to stay within memory limits.
# Use threads for concurrency (I/O-bound LLM calls benefit greatly).
workers = 1
threads = 4                     # 4 threads per worker = 4 concurrent requests
worker_class = "gthread"        # thread-based, no gevent dependency needed

# ── Timeouts ─────────────────────────────────────────────────
# LLM & SEO calls can be slow; give them 120 s before killing a worker.
timeout = 120
graceful_timeout = 30
keepalive = 5

# ── Logging ───────────────────────────────────────────────────
loglevel = "info"
accesslog = "-"     # stdout → Render log stream
errorlog  = "-"     # stderr → Render log stream
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sμs'

# ── Process naming ────────────────────────────────────────────
proc_name = "jarvis"

# ── Preload (disabled for free tier — saves RAM on restarts) ──
preload_app = False

# ── Limits ────────────────────────────────────────────────────
max_requests        = 500       # recycle worker after N requests (memory guard)
max_requests_jitter = 50        # random jitter to avoid thundering herd

# ── Server hooks (health logging) ────────────────────────────
def on_starting(server):
    server.log.info("🚀 J.A.R.V.I.S. Gunicorn starting up...")

def post_fork(server, worker):
    server.log.info(f"  Worker {worker.pid} forked and ready.")

def worker_exit(server, worker):
    server.log.info(f"  Worker {worker.pid} exited.")
