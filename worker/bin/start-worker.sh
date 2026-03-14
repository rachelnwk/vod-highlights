#!/bin/bash

set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORKER_DIR="$APP_ROOT/worker"
WORKER_VENV_DIR="${WORKER_VENV_DIR:-/var/worker-venv}"

if [[ ! -x "$WORKER_VENV_DIR/bin/python" ]]; then
  echo "Worker virtual environment not found at $WORKER_VENV_DIR" >&2
  exit 1
fi

export PYTHONUNBUFFERED=1

cd "$WORKER_DIR"
exec "$WORKER_VENV_DIR/bin/python" worker.py
