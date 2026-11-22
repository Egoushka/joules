#!/bin/bash
# Synthetic inputs, made on the Mac with `say`. No mic, no camera, no personal files.
set -euo pipefail
D="${1:-$HOME/joules-spike/inputs}"; mkdir -p "$D"
say -v Samantha -r 170 -o "$D/clip.aiff" "The quick brown fox jumps over the lazy dog. Energy per task is the number that matters, so we measure it in joules, one run at a time, on this very machine."
afconvert -f WAVE -d LEI16@16000 -c 1 "$D/clip.aiff" "$D/clip.wav"
afinfo "$D/clip.wav" | grep 'estimated duration'
