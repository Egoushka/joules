#!/bin/bash
# Run step (offline). Idle baseline, noop check, then 5 interleaved rounds of the 3 tasks.
set -u
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PATH="$HOME/.cargo/bin:$PATH"
PY=env/venv/bin/python
PAIR="${PAIR:-}"
rm -f runs.ndjson idle.json
python3 joules.py idle --seconds 30 --sample-ms ${MS:-250}
for i in 1 2 3; do python3 joules.py run $PAIR --sample-ms ${MS:-250} --label noop -- sleep 5; done
for i in 1 2 3 4 5; do
  python3 joules.py run $PAIR --sample-ms ${MS:-250} --label stt   -- bash tasks/stt.sh
  python3 joules.py run $PAIR --sample-ms ${MS:-250} --label hands -- $PY tasks/hands.py
  python3 joules.py run $PAIR --sample-ms ${MS:-250} --label llm   -- $PY tasks/llm.py
done
python3 joules.py report
echo MEASURE_DONE
