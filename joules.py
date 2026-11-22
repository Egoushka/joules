#!/usr/bin/env python3
"""joules: run a command, report the energy it used (macOS, macmon sampler).

  joules idle --seconds 30
  joules run --label L -- <cmd...>
  joules report

Power is integrated over the command's wall-clock window from timed samples.
Net figures subtract the idle baseline (mean idle watts x seconds) per channel.
Stdlib only, Python 3.9+.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time

CHANNELS = ("total", "cpu", "gpu", "ane")
MACMON_KEYS = {"total": "all_power", "cpu": "cpu_power", "gpu": "gpu_power", "ane": "ane_power"}
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.environ.get("JOULES_RUNS", os.path.join(HERE, "runs.ndjson"))
IDLE = os.environ.get("JOULES_IDLE", os.path.join(HERE, "idle.json"))


# --- integration -----------------------------------------------------------

def integrate(samples, t0, t1):
    """samples: [(t_end, interval_s, {channel: watts})]; each sample is the mean power over
    (t_end - interval_s, t_end]. Returns ({channel: joules}, n_samples) over [t0, t1],
    counting each sample by its overlap with the window."""
    joules = {c: 0.0 for c in CHANNELS}
    n = 0
    for t_end, dt, w in samples:
        lo, hi = max(t_end - dt, t0), min(t_end, t1)
        if hi <= lo:
            continue
        n += 1
        for c in CHANNELS:
            joules[c] += w.get(c, 0.0) * (hi - lo)
    return joules, n


# --- samplers --------------------------------------------------------------

class MacmonSampler:
    """`macmon pipe` in a subprocess, read by a thread. No sudo."""
    name = "macmon"

    def __init__(self, sample_ms=250):
        self.sample_ms = sample_ms
        self.samples = []
        self._lock = threading.Lock()
        exe = shutil.which("macmon") or os.path.expanduser("~/.cargo/bin/macmon")
        self._p = subprocess.Popen([exe, "pipe", "-i", str(sample_ms)], stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        self._t = threading.Thread(target=self._read, daemon=True)
        self._t.start()
        self._wait_first()

    def _read(self):
        prev = None
        for line in self._p.stdout:
            try:
                d = json.loads(line)
                t = datetime.datetime.fromisoformat(d["timestamp"]).timestamp()  # end of its interval
            except (ValueError, KeyError):
                continue
            w = {c: float(d.get(k) or 0.0) for c, k in MACMON_KEYS.items()}
            dt = (t - prev) if prev is not None else self.sample_ms / 1000.0
            prev = t
            with self._lock:
                self.samples.append((t, dt, w))

    def _wait_first(self):
        end = time.time() + 10
        while time.time() < end:
            with self._lock:
                if self.samples:
                    return
            time.sleep(0.05)
        raise RuntimeError("macmon produced no rows")

    def snapshot(self):
        with self._lock:
            return list(self.samples)

    def settle(self):
        time.sleep(self.sample_ms / 1000.0 * 1.6)  # let the last interval land

    def close(self):
        self._p.terminate()


class FakeSampler:
    """Constant power, for tests: `watts` for `seconds`, one row per `sample_ms`, from t=start."""
    name = "fake"

    def __init__(self, watts=2.0, seconds=10.0, sample_ms=250, start=0.0):
        dt = sample_ms / 1000.0
        n = int(round(seconds / dt))
        self.sample_ms = sample_ms
        w = {"total": watts, "cpu": watts, "gpu": 0.0, "ane": 0.0}
        self.samples = [(start + (i + 1) * dt, dt, w) for i in range(n)]

    def snapshot(self):
        return list(self.samples)

    def settle(self):
        pass

    def close(self):
        pass


def make_sampler(sample_ms):
    return MacmonSampler(sample_ms)


# --- measuring -------------------------------------------------------------

def measure(sampler, fn):
    """Run fn() (returns anything) inside an energy window. Returns dict with window stats."""
    start = time.time()
    p0 = time.perf_counter()
    result = fn()
    seconds = time.perf_counter() - p0
    end = start + seconds
    sampler.settle()
    joules, n = integrate(sampler.snapshot(), start, end)
    return {"start": start, "seconds": seconds, "joules": joules, "n_samples": n, "result": result}


def load_idle():
    if not os.path.exists(IDLE):
        return None
    with open(IDLE) as f:
        return json.load(f)


def cmd_idle(a):
    s = make_sampler(a.sample_ms)
    try:
        m = measure(s, lambda: time.sleep(a.seconds))
    finally:
        s.close()
    watts = {c: m["joules"][c] / m["seconds"] for c in CHANNELS}
    rec = {"measured": iso(m["start"]), "seconds": m["seconds"], "sampler": s.name,
           "sample_ms": a.sample_ms, "watts": watts, "n_samples": m["n_samples"]}
    with open(IDLE, "w") as f:
        json.dump(rec, f, indent=1)
    print("idle baseline: " + "  ".join("%s=%.3fW" % (c, watts[c]) for c in CHANNELS))
    return 0


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


TOKENS = re.compile(r"\btokens=(\d+)")


def run_command(cmd):
    tokens = [None]

    def go():
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=None, text=True)
        for line in p.stdout:
            sys.stdout.write(line)
            m = TOKENS.search(line)
            if m:
                tokens[0] = int(m.group(1))
        return p.wait()
    return go, tokens


def timed_idle(sampler, seconds):
    m = measure(sampler, lambda: time.sleep(seconds))
    return {c: m["joules"][c] / m["seconds"] for c in CHANNELS}


def cmd_run(a):
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        sys.exit("joules run: no command")
    idle = load_idle()
    s = make_sampler(a.sample_ms)
    try:
        pre = timed_idle(s, a.pair_idle) if a.pair_idle else None
        go, tokens = run_command(cmd)
        m = measure(s, go)
        post = timed_idle(s, a.pair_idle) if a.pair_idle else None
    finally:
        s.close()
    sec, J = m["seconds"], m["joules"]
    rec = {"label": a.label, "start": iso(m["start"]), "seconds": round(sec, 3)}
    for c in CHANNELS:
        rec["joules_" + c] = round(J[c], 3)
    rec["avg_w"] = round(J["total"] / sec, 3)
    if pre:  # idle measured right before and after this run: tracks drift in background load
        idle = {"watts": {c: (pre[c] + post[c]) / 2 for c in CHANNELS}}
        rec["baseline"] = "paired%gs" % a.pair_idle
    elif idle:
        rec["baseline"] = "idle.json"
    if idle:
        iw = idle["watts"]
        for c in CHANNELS:
            rec["net_joules_" + c] = round(J[c] - iw[c] * sec, 3)
        rec["net_avg_w"] = round(rec["net_joules_total"] / sec, 3)
        rec["idle_w"] = round(iw["total"], 3)
    rec.update(sampler=s.name, sample_ms=a.sample_ms, n_samples=m["n_samples"], exit_code=m["result"])
    if tokens[0] is not None:
        rec["tokens"] = tokens[0]
    with open(RUNS, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), file=sys.stderr)
    return m["result"]


def cmd_report(a):
    rows = {}
    if os.path.exists(RUNS):
        with open(RUNS) as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    rows.setdefault(r["label"], []).append(r)
    if not rows:
        print("no runs")
        return 1
    hdr = ("label", "n", "sec", "raw J med", "net J med", "net min", "net max", "spread", "avg W", "tok", "J/tok")
    out = [hdr]
    for label, rs in sorted(rows.items()):
        net = [r.get("net_joules_total", r["joules_total"]) for r in rs]
        med = statistics.median(net)
        spread = (max(net) - min(net)) / med if med else float("nan")
        toks = [r["tokens"] for r in rs if "tokens" in r]
        tok = statistics.median(toks) if toks else None
        out.append((label, str(len(rs)), "%.2f" % statistics.median(r["seconds"] for r in rs),
                    "%.2f" % statistics.median(r["joules_total"] for r in rs), "%.2f" % med,
                    "%.2f" % min(net), "%.2f" % max(net), "%.1f%%" % (spread * 100),
                    "%.2f" % statistics.median(r["avg_w"] for r in rs),
                    "%d" % tok if tok else "-", "%.3f" % (med / tok) if tok else "-"))
    widths = [max(len(r[i]) for r in out) for i in range(len(hdr))]
    for r in out:
        print("  ".join(v.rjust(w) if i else v.ljust(w) for i, (v, w) in enumerate(zip(r, widths))))
    print("\nsplit (median raw J): cpu / gpu / ane")
    for label, rs in sorted(rows.items()):
        print("  %-10s %s" % (label, " / ".join("%.2f" % statistics.median(r["joules_" + c] for r in rs)
                                                 for c in ("cpu", "gpu", "ane"))))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="joules")
    sub = ap.add_subparsers(dest="sub", required=True)
    p = sub.add_parser("idle")
    p.add_argument("--seconds", type=float, default=30)
    p.add_argument("--sample-ms", type=int, default=250)
    p.set_defaults(f=cmd_idle)
    p = sub.add_parser("run")
    p.add_argument("--label", required=True)
    p.add_argument("--sample-ms", type=int, default=250)
    p.add_argument("--pair-idle", type=float, default=0,
                   help="seconds of idle to measure before and after the run; replaces idle.json for this run")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    p.set_defaults(f=cmd_run)
    p = sub.add_parser("report")
    p.set_defaults(f=cmd_report)
    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
