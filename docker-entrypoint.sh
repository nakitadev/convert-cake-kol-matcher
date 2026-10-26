#!/bin/sh
set -e

echo "=== Starting Convert Cake Thai TikTok KOL Matcher in Docker ==="

# 1. Start FastAPI Backend in background
echo "[1/2] Starting FastAPI Backend on :8000..."
cd /app/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 2. Start Next.js Frontend
echo "[2/2] Starting Next.js Frontend on :3000..."
cd /app/frontend
npm start &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

echo ""
echo "🚀 Convert Cake is running!"
echo "   • Frontend: http://localhost:3000"
echo "   • Backend API: http://localhost:8000"
echo ""

wait
