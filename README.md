# joules: joules-per-task meter (macOS, spike)

`joules run --label L -- <cmd>` samples SoC power with `macmon pipe` (no sudo) while `<cmd>` runs and appends
one JSON line to `runs.ndjson`. `joules idle --seconds 30` takes a baseline; `joules report` prints median,
min/max and spread per label. `--pair-idle S` measures S seconds of idle before and after the run and uses
their mean as the baseline (tracks background-load drift). `tokens=N` on the command's stdout is recorded.

Setup (once, networked): `scripts/setup.sh`. Run step is offline: `scripts/measure_all.sh`, `scripts/check_nonet.sh`.
Tasks: `tasks/` (whisper.cpp base.en on a `say` clip; MediaPipe HandLandmarker 60 s at 30 fps on synthetic frames;
mlx-lm Qwen2.5-0.5B-Instruct-4bit, 200 greedy tokens, EOS suppressed). Tests: `python3 -m unittest`.

Installed on the Mac: macmon 0.12.0 (cargo), cmake + uv (pip --user), whisper.cpp (source build) + ggml-base.en,
a Python 3.12 venv (numpy, mediapipe 1.2.3, mlx-lm, opencv-python-headless, huggingface_hub), hand_landmarker.task,
Qwen weights. All under `~/joules-spike/env`.

## Results (M1, macOS 27.0.1, a live desktop in use; net = minus idle baseline)

| label | n | sec | net J median | min | max | spread | note |
|---|---|---|---|---|---|---|---|
| hands | 5 | 60.98 | 139.1 | 135.9 | 161.8 | 18.6% | paired 6 s idle, 200 ms |
| llm | 5 | 3.31 | 20.3 | 19.7 | 20.8 | 5.6% | 0.102 J/token (net) |
| stt | 5 | 0.81 | 3.03 | 2.99 | 3.48 | 16.0% | paired 15 s idle, 100 ms |
| noop (sleep 5) | 5 | 5.02 | 0.73 | -0.52 | 7.20 | n/a | one 7.2 J outlier |

Raw data: `results/`. First pass with one global 30 s baseline was worse (hands 55%, llm 38%, stt 43%).
ANE reads 0.00 W on every task. macmon works on macOS 27.0.1 (non-zero rows), so powermetrics was not needed.
