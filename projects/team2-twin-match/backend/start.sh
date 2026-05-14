#!/usr/bin/env bash
set -euo pipefail

export ENV="${ENV:-local}"

mkdir -p data

poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
