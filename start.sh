#!/bin/bash

# ASL Form Correction App - Real-time Analysis Startup Script
# This script starts both the FastAPI backend and React frontend

set -e  # Exit on any error

echo "🚀 Starting Real-time ASL Form Correction Application"
echo "===================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "Please run this script from the my-react-app directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if Node.js is available
if ! command -v npm &> /dev/null; then
    print_error "Node.js and npm are required but not installed"
    exit 1
fi

print_status "Checking dependencies..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    print_status "Installing Node.js dependencies..."
    npm install
fi

# Check if Python backend dependencies are installed
if [ ! -d "fastapi-backend/venv" ]; then
    print_status "Setting up Python virtual environment..."
    cd fastapi-backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

print_success "All dependencies are ready!"

# Function to cleanup background processes
cleanup() {
    print_status "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

print_status "Testing AWS Bedrock connection..."

# Test Bedrock connection
cd fastapi-backend
source venv/bin/activate
python test_bedrock.py
echo ""

print_status "Starting FastAPI backend server..."

# Start the FastAPI backend in the background
python main.py &
BACKEND_PID=$!
cd ..

# Wait a moment for the backend to start
sleep 3

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    print_error "Backend failed to start. Check the logs above."
    cleanup
fi

print_success "FastAPI backend is running on http://localhost:8000"

print_status "Starting React frontend..."

# Start the React frontend
npm start &
FRONTEND_PID=$!

print_success "React frontend is starting on http://localhost:3000"

echo ""
echo "🎉 Real-time ASL Analysis Application is starting up!"
echo "===================================================="
echo "• FastAPI Backend: http://localhost:8000"
echo "• React Frontend: http://localhost:3000"
echo ""
echo "Features:"
echo "• Upload target videos for any ASL sign"
echo "• Real-time pose comparison using MediaPipe"
echo "• AI-powered feedback from AWS Bedrock"
echo "• Instant visual feedback with skeleton overlay"
echo ""
echo "The React app should open in your browser automatically."
echo "Press Ctrl+C to stop both servers."
echo ""

# Wait for both processes
wait