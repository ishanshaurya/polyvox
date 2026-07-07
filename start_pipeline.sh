#!/usr/bin/env bash
# Detached pipeline launcher (use when tmux unavailable)
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
set -a
source .env
set +a
exec ./run_pipeline.sh 2>&1 | tee -a pipeline_run.log
