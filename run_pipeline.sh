#!/usr/bin/env bash
# Full pipeline: transcribe + analyze all batches, then cumulative Excel.
# See the README quick start.
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
set -a
source .env
set +a

export PIPELINE_CONFIG="${PIPELINE_CONFIG:-config.yaml}"

NUM_BATCHES=$(python -c "from pipeline_config import load_config; from callqa.state import manifest; print(manifest.max_batch(manifest.load(load_config())))")
if [ "$NUM_BATCHES" -eq 0 ]; then
  echo "No calls in manifest — run python 0_fetch_csv.py first" >&2
  exit 1
fi
echo "Config: $PIPELINE_CONFIG"
echo "Running $NUM_BATCHES batch(es)"

for N in $(seq 1 "$NUM_BATCHES"); do
  echo "=== BATCH $N ==="
  python 1_transcribe.py --batch "$N" || echo "WARN: transcribe batch $N had errors"
  python 2_analyze.py --batch "$N" || echo "WARN: analyze batch $N had errors"
done
python 3_report.py --batch "$NUM_BATCHES"
OUT=$(python -c 'from pipeline_config import load_config; print(load_config()["output_folder"])')
echo "PIPELINE COMPLETE — reports in ${OUT}/reports/"
