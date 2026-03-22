#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Resetting trading database tables..."
./.venv/bin/python -m app.scripts.reset_db

echo "Recreating seed row..."
./.venv/bin/python -m app.scripts.seed

echo "Trading database reset completed."
