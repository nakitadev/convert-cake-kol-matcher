#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Starting Convert Cake Thai TikTok KOL Matcher ==="

# 1. Start Backend
echo "[1/2] Starting FastAPI Backend on http://localhost:8000..."
source venv/bin/activate
export PYTHONPATH="$PROJECT_DIR/backend:$PROJECT_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend/app &
BACKEND_PID=$!

# 2. Start Frontend
echo "[2/2] Starting Next.js 16 Frontend on http://localhost:3000..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

echo ""
echo "🚀 System is live!"
echo "   • Dashboard UI: http://localhost:3000"
echo "   • API & Swagger: http://localhost:8000/docs"
echo "Press Ctrl+C to stop both servers."
echo ""

wait
