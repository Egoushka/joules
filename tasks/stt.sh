#!/bin/bash
# Task 1: whisper.cpp base.en on the fixed synthetic clip. Offline.
E="${JE:-$HOME/joules-spike/env}"; I="${JI:-$HOME/joules-spike/inputs}"
exec "$E/whisper.cpp/build/bin/whisper-cli" -m "$E/whisper.cpp/models/ggml-base.en.bin" -f "$I/clip.wav" -nt -t 4 >/dev/null 2>"${TMPDIR:-/tmp}/stt.err"
