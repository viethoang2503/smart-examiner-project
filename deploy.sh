#!/bin/bash
# FocusGuard Deployment Script
# Deploys server and client on Linux/macOS

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "========================================"
echo "FocusGuard Deployment Script"
echo "========================================"

# Check Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON=python3
    elif command -v python &> /dev/null; then
        PYTHON=python
    else
        echo "❌ Python not found!"
        exit 1
    fi
    echo "✅ Using: $($PYTHON --version)"
}

# Create virtual environment
setup_venv() {
    echo ""
    echo "📦 Setting up virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        $PYTHON -m venv "$VENV_DIR"
        echo "✅ Virtual environment created"
    else
        echo "✅ Virtual environment exists"
    fi
    
    source "$VENV_DIR/bin/activate"
}

# Install dependencies
install_deps() {
    echo ""
    echo "📦 Installing dependencies..."
    
    pip install --upgrade pip -q
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    
    echo "✅ Dependencies installed"
}

# Initialize database
init_db() {
    echo ""
    echo "🗄️ Initializing database..."
    
    if [ -f "$PROJECT_DIR/init_database.py" ]; then
        $PYTHON "$PROJECT_DIR/init_database.py"
    else
        $PYTHON -c "from server.database import init_db; init_db()"
    fi
    
    echo "✅ Database initialized"
}

# Start server
start_server() {
    echo ""
    echo "🚀 Starting FocusGuard Server..."
    echo "   URL: http://localhost:8000"
    echo "   Press Ctrl+C to stop"
    echo ""
    
    $PYTHON "$PROJECT_DIR/run_server.py"
}

# Start client
start_client() {
    echo ""
    echo "🚀 Starting FocusGuard Client..."
    
    $PYTHON "$PROJECT_DIR/run_client.py"
}

# Main
main() {
    check_python
    setup_venv
    install_deps
    
    case "${1:-server}" in
        server)
            init_db
            start_server
            ;;
        client)
            start_client
            ;;
        install)
            init_db
            echo ""
            echo "✅ Installation complete!"
            echo "   Run: ./deploy.sh server"
            echo "   Or:  ./deploy.sh client"
            ;;
        *)
            echo "Usage: $0 {server|client|install}"
            exit 1
            ;;
    esac
}

main "$@"
