#!/bin/bash
set -euo pipefail

# Conductor Setup Script for Points Project
# This script sets up a new workspace with all necessary dependencies and configurations

# Default so `set -u` doesn't abort when run outside Conductor (var is Conductor-only)
CONDUCTOR_ROOT_PATH="${CONDUCTOR_ROOT_PATH:-}"

echo "🚀 Setting up Points workspace..."

# Check for required tools
echo "📋 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed. Please install Node.js 16+ first."
    exit 1
fi

# Backend Setup
echo "🔧 Setting up backend..."
cd backend

# Create virtual environment
echo "  Creating Python virtual environment..."
python3 -m venv env

# Activate virtual environment
source env/bin/activate

# Install Python dependencies
echo "  Installing Python packages..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Setup Node.js environment in the virtual environment (skip if system Node.js available)
if command -v node &> /dev/null; then
    echo "  Using system Node.js ($(node -v))..."
else
    echo "  Setting up Node.js environment..."
    nodeenv -p --quiet
fi

# Copy environment file if it exists in root
if [ -f "$CONDUCTOR_ROOT_PATH/backend/.env" ]; then
    echo "  Copying backend .env file..."
    cp "$CONDUCTOR_ROOT_PATH/backend/.env" .env
elif [ -f ".env.example" ]; then
    echo "  Creating .env from .env.example..."
    cp .env.example .env
    echo "  ⚠️  Please update backend/.env with your actual configuration values"
fi

# Run database migrations
echo "  Running database migrations..."
python manage.py migrate --noinput

# Frontend Setup
echo "🎨 Setting up frontend..."
cd ../frontend

# Install frontend dependencies
echo "  Installing npm packages..."
npm install --silent

# Copy frontend environment file if it exists
if [ -f "$CONDUCTOR_ROOT_PATH/frontend/.env" ]; then
    echo "  Copying frontend .env file..."
    cp "$CONDUCTOR_ROOT_PATH/frontend/.env" .env
elif [ -f ".env.example" ]; then
    echo "  Creating .env from .env.example..."
    cp .env.example .env
    echo "  ⚠️  Please update frontend/.env with your actual configuration values"
fi

echo "✅ Workspace setup complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Review and update any .env files if needed"
echo "  2. Click the 'Run' button to start the development servers"
echo ""