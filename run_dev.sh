#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Check if docker flag requested
if [ "$1" == "--docker" ] || [ "$1" == "docker" ]; then
  echo "🐳 Launching Convert Cake via Docker Compose..."
  docker compose up --build
  exit 0
fi

echo "=== Starting Convert Cake Thai TikTok KOL Matcher ==="
echo "Tip: You can also launch with Docker Compose using: docker compose up --build (or ./run_dev.sh --docker)"
echo ""

# 1. Start Backend
echo "[1/2] Starting FastAPI Backend on http://localhost:8000..."
source venv/bin/activate
export PYTHONPATH="$PROJECT_DIR/backend:$PROJECT_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend/app &
BACKEND_PID=$!

# 2. Start Frontend
echo "[2/2] Starting Vite React Frontend on http://localhost:3000..."
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
