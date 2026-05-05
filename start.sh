#!/bin/bash
set -e

echo "=========================================="
echo "  Add-CreatZ — Starting Application Stack"
echo "=========================================="

# ── Fix API URLs for HuggingFace deployment ──────────────────
# These sed commands modify ONLY the container's copy of the files.
# Your original source code files remain 100% untouched.
echo "[1/6] Patching API URLs for cloud deployment..."

# Fix main API URL: http://127.0.0.1:8100 → (empty, becomes relative)
# This makes fetch('/generate', ...) which nginx routes to port 8100
sed -i "s|http://127.0.0.1:8100||g" /app/index.html

# Fix Facebook service URLs: http://127.0.0.1:8101/ → /fb/
# This makes fetch('/fb/prepare_post', ...) which nginx routes to port 8101
sed -i "s|http://127.0.0.1:8101/|/fb/|g" /app/index.html

# Fix Facebook callback redirect to use relative path
sed -i "s|http://localhost:8080/index.html|/index.html|g" /app/facebook_poster/fb_server.py

echo "[1/6] ✅ API URLs patched successfully."

# ── Start the frontend static file server ────────────────────
echo "[2/6] Starting frontend server on port 8080..."
cd /app && python -m http.server 8080 &
FRONTEND_PID=$!

# ── Start the main AI backend ────────────────────────────────
echo "[3/6] Starting main API server on port 8100..."
cd /app && python main.py &
MAIN_PID=$!

# ── Start the Facebook posting service ───────────────────────
echo "[4/6] Starting Facebook service on port 8101..."
cd /app && python -c "
import sys
sys.path.insert(0, '/app/facebook_poster')
import uvicorn
from fb_server import app
uvicorn.run(app, host='0.0.0.0', port=8101)
" &
FB_PID=$!

# ── Wait for backends to initialize ─────────────────────────
echo "[5/6] Waiting for services to initialize..."
sleep 5

# ── Start nginx reverse proxy (foreground) ───────────────────
echo "[6/6] Starting nginx reverse proxy on port 7860..."
echo "=========================================="
echo "  App is live on port 7860"
echo "=========================================="
nginx -g "daemon off;"
