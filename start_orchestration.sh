#!/bin/bash
# S2 Intelligence - Multi-Agent Orchestration Startup Script
# Starts all services in separate terminal tabs

echo "======================================================================"
echo "S2 INTELLIGENCE - MULTI-AGENT ORCHESTRATION"
echo "Starting all services..."
echo "======================================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.8+"
    exit 1
fi
echo "✓ Python found: $(python3 --version)"

# Check dependencies
echo "Checking dependencies..."
python3 -c "import fastapi, uvicorn, pydantic, requests, jwt, psutil" 2>&1 > /dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements_orchestration.txt
fi
echo "✓ Dependencies ready"
echo ""

# Create log directory
mkdir -p logs

# Start services in background
echo "Starting Egregore Service Manager (Port 9000)..."
python3 egregore_service_manager.py > logs/egregore_manager.log 2>&1 &
EGREGORE_PID=$!
sleep 2

echo "Starting Intelligence Router (Port 3011)..."
python3 intelligence_router_production.py > logs/intelligence_router.log 2>&1 &
ROUTER_PID=$!
sleep 2

echo "Starting API Gateway (Port 8000)..."
python3 api_gateway.py > logs/api_gateway.log 2>&1 &
API_PID=$!
sleep 2

echo ""
echo "======================================================================"
echo "ALL SERVICES STARTED!"
echo "======================================================================"
echo ""
echo "Services:"
echo "  • Egregore Manager:    http://localhost:9000  (PID: $EGREGORE_PID)"
echo "  • Intelligence Router: http://localhost:3011  (PID: $ROUTER_PID)"
echo "  • API Gateway:         http://localhost:8000  (PID: $API_PID)"
echo "  • API Documentation:   http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  • Egregore Manager:    logs/egregore_manager.log"
echo "  • Intelligence Router: logs/intelligence_router.log"
echo "  • API Gateway:         logs/api_gateway.log"
echo ""
echo "Dashboard:"
echo "  Open orchestration_dashboard.html in browser"
echo ""
echo "Test:"
echo '  curl -X POST http://localhost:8000/v1/query \'
echo '    -H "X-API-Key: sk-demo-key" \'
echo '    -H "Content-Type: application/json" \'
echo '    -d "{\"query\": \"How do I design a scalable system?\"}"'
echo ""
echo "To stop services:"
echo "  kill $EGREGORE_PID $ROUTER_PID $API_PID"
echo ""
echo "Press Ctrl+C to stop all services..."

# Handle Ctrl+C
trap "echo ''; echo 'Stopping services...'; kill $EGREGORE_PID $ROUTER_PID $API_PID 2>/dev/null; exit 0" INT

# Wait
wait
