#!/bin/bash

# Ensure we start at the root of the project where this script lives
cd "$(dirname "$0")"

echo "🚀 Booting up the Agent Workforce Control Plane (AWCP)..."

echo "📦 1. Starting Evidence Vault & Policy Engine (Docker)..."
cd 04_Evidence_Substrate_Infra
docker-compose up -d
cd ..

echo "⏱️  2. Starting Temporal Orchestrator..."
temporal server start-dev &
TEMPORAL_PID=$!
sleep 4 # Give Temporal 4 seconds to fully wake up

echo "👷 3. Starting Temporal Worker..."
cd 02_Durable_Orchestration_Backend
source venv/bin/activate
python worker.py &
WORKER_PID=$!
cd ..

echo "🚪 4. Starting Intake Proxy (FastAPI)..."
cd 02_Durable_Orchestration_Backend
source venv/bin/activate
python -m uvicorn intake_proxy:app --reload --port 8000 &
PROXY_PID=$!
cd ..

echo "💻 5. Starting Operator Surface (React UI)..."
# --- THE FIX: We navigate into the dashboard folder! ---
cd 03_Risk_First_Operator_UI/dashboard
npm start &
UI_PID=$!
cd ../..

echo "✅ ALL SYSTEMS GO! AWCP is fully armed and operational."
echo "Press [Ctrl + C] to safely shut everything down."

# This catches the Ctrl+C and cleanly kills all the background tasks!
trap "echo '🛑 Shutting down AWCP...'; kill $TEMPORAL_PID $WORKER_PID $PROXY_PID $UI_PID; exit" INT TERM EXIT
wait