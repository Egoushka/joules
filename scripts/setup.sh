#!/bin/bash
# One-time, networked step. Run on the Mac. Everything lands in $J (default ~/joules-spike/env).
# Installs: macmon (cargo), cmake + uv (pip --user), whisper.cpp (source build) + ggml-base.en,
#           python 3.12 venv with numpy, mediapipe, mlx-lm; Qwen2.5-0.5B-Instruct-4bit weights.
set -euo pipefail
export PATH="$HOME/.cargo/bin:$HOME/Library/Python/3.9/bin:$HOME/.local/bin:$PATH"
J="${J:-$HOME/joules-spike/env}"
mkdir -p "$J"; cd "$J"

command -v macmon >/dev/null || cargo install macmon
command -v cmake  >/dev/null || python3 -m pip install --user cmake
command -v uv     >/dev/null || python3 -m pip install --user uv

if [ ! -x whisper.cpp/build/bin/whisper-cli ]; then
  TAG=$(curl -fsS https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest | python3 -c 'import sys,json;print(json.load(sys.stdin)["tag_name"])')
  echo "whisper.cpp $TAG"
  rm -rf whisper.cpp; mkdir whisper.cpp
  curl -fsSL "https://github.com/ggml-org/whisper.cpp/archive/refs/tags/$TAG.tar.gz" | tar xz --strip-components=1 -C whisper.cpp
  (cd whisper.cpp && cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j 8 --config Release --target whisper-cli)
fi
[ -f whisper.cpp/models/ggml-base.en.bin ] || curl -fsSL -o whisper.cpp/models/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin

[ -d venv ] || uv venv --python 3.12 venv
uv pip install --python venv/bin/python numpy mediapipe mlx-lm opencv-python-headless huggingface_hub
venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
print(snapshot_download("mlx-community/Qwen2.5-0.5B-Instruct-4bit"))
PY
echo SETUP_DONE
# MediaPipe 1.x has no bundled `solutions`; the Tasks API needs this model file (one-time download).
[ -f "$J/hand_landmarker.task" ] || curl -fsSL -o "$J/hand_landmarker.task" \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
