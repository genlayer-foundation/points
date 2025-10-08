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

trap cleanup EXIT INT TERM

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

# Use CONDUCTOR_PORT if available, otherwise default to 5173
FRONTEND_PORT=${CONDUCTOR_PORT:-5173}
npm run dev -- --port $FRONTEND_PORT --host &
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