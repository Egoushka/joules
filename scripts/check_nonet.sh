#!/bin/bash
# Acceptance 5: the run step works with the network denied. Wi-Fi can't be switched off (it carries the ssh
# session), so each task runs under a macOS sandbox profile that denies all outbound and inbound network.
# Also polls lsof for any internet socket opened by the task's process tree.
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HANDS_SECONDS=8
PROF='(version 1)(allow default)(deny network*)'
rc=0
for t in "bash tasks/stt.sh" "env/venv/bin/python tasks/hands.py" "env/venv/bin/python tasks/llm.py"; do
  : > /tmp/nonet.lsof
  sandbox-exec -p "$PROF" $t >/tmp/nonet.out 2>&1 & pid=$!
  while kill -0 $pid 2>/dev/null; do lsof -nP -i -a -p "$pid,$(pgrep -P $pid | paste -sd, -)" >>/tmp/nonet.lsof 2>/dev/null; sleep 0.3; done
  wait $pid; e=$?
  n=$(grep -c -E 'TCP|UDP' /tmp/nonet.lsof)
  echo "$t -> exit=$e internet_sockets_seen=$n"; [ $e -eq 0 ] && [ $n -eq 0 ] || rc=1
done
[ $rc -eq 0 ] && echo NONET_OK || echo NONET_FAIL
