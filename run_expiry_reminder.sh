#!/bin/bash

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

export RECORDED_BASE_DIR="$APP_DIR"
export RECORDED_DB_PATH="$APP_DIR/data.db"

cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" -m expiry_backend.run_reminders
