#!/usr/bin/env bash
# Full pipeline: transcribe + analyze all batches, then cumulative Excel.
# See PIPELINE_RUNBOOK.md for step-by-step instructions.
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
set -a
source .env
set +a

export PIPELINE_CONFIG="${PIPELINE_CONFIG:-config.yaml}"

NUM_BATCHES=$(python -c "from pipeline_config import load_config; c=load_config(); print(int(c['fetch_limit']) // int(c['batch_size']))")
echo "Config: $PIPELINE_CONFIG"
echo "Running $NUM_BATCHES batch(es) (fetch_limit=$(python -c 'from pipeline_config import load_config; c=load_config(); print(c["fetch_limit"])') batch_size=$(python -c 'from pipeline_config import load_config; c=load_config(); print(c["batch_size"])'))"

for N in $(seq 1 "$NUM_BATCHES"); do
  echo "=== BATCH $N ==="
  python 1_transcribe.py --batch "$N" || echo "WARN: transcribe batch $N had errors"
  python 2_analyze.py --batch "$N" || echo "WARN: analyze batch $N had errors"
done
python 3_report.py --batch "$NUM_BATCHES"
OUT=$(python -c 'from pipeline_config import load_config; print(load_config()["output_folder"])')
echo "PIPELINE COMPLETE — reports in ${OUT}/reports/"
