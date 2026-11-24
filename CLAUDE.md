# joules

Energy-per-task meter for Apple Silicon Macs (macmon sampler). Read README.md first.

- The tasks run on the Mac (`ssh mac`), not the devbox: macmon needs macOS. The runtime is in `~/joules-spike/env` there; `python3 -m unittest` runs anywhere.
- Measure on a quiet Mac: check `uptime` and `ps` first, and record the load in the README with any new table. A busy desktop made the 2026-11-24 spread 50%.
- `runs.ndjson` is git-ignored scratch. Commit finished runs as `results/runs.<name>.ndjson`; check they hold only numbers and UTC timestamps (no paths, hostnames, transcripts).
- Open items are listed under "Numbers" in the README; update them when a run changes them. No sudo on the Mac, so powermetrics cannot be run from here.
