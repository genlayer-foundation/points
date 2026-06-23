#!/bin/bash
set -euo pipefail

# Conductor Run Script for Points Project
# This script starts both backend and frontend development servers

echo "🚀 Starting Points development servers..."

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill 0 2>/dev/null || true
    exit
}

# Conductor stops a run by sending SIGHUP, so trap it too or cleanup never fires.
trap cleanup EXIT INT TERM HUP

# Start Backend Server
echo "🔧 Starting Django backend server..."
cd backend
source env/bin/activate
python manage.py runserver 8000 &
BACKEND_PID=$!
echo "  Backend running on http://localhost:8000"

# Give backend a moment to start
sleep 2

# Start Frontend Server
echo "🎨 Starting Svelte frontend server..."
cd ../frontend

# Fixed port 5173: backend SIWE_DOMAIN, FRONTEND_URL and CSRF/CORS origins all
# expect the frontend at localhost:5173 (see backend/tally/settings.py). OAuth/SIWE
# redirects break on any other port. --strictPort makes Vite fail loudly instead of
# silently drifting to 5174.
FRONTEND_PORT=5173
npm run dev -- --port $FRONTEND_PORT --strictPort --host &
FRONTEND_PID=$!
echo "  Frontend running on http://localhost:$FRONTEND_PORT"

echo ""
echo "✅ All servers started successfully!"
echo ""
echo "📝 Available endpoints:"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Backend API: http://localhost:8000/api/"
echo "  Django Admin: http://localhost:8000/admin/"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID