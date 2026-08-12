#!/bin/bash
# Launches the 5 stage services and the API gateway together.
# Run from the homework-6 root: bash scripts/start-services.sh
set -e

cd "$(dirname "$0")/.."

python3 -m uvicorn services.validation.main:app --port 8001 &
python3 -m uvicorn services.fraud_detection.main:app --port 8002 &
python3 -m uvicorn services.compliance.main:app --port 8003 &
python3 -m uvicorn services.settlement.main:app --port 8004 &
python3 -m uvicorn services.reporting.main:app --port 8005 &
python3 -m uvicorn gateway.main:app --port 8010 &

wait
