"""Print g3_matrix output as one readable line per run."""
import json
import sys

for line in sys.stdin:
    if line.startswith("{"):
        r = json.loads(line)
        print(
            "OK " if r["ok"] else "BAD", r["case"], r["persona"], r["arch"][:3], r["strategy"], r["latency_s"],
            "| proposed", r["proposed"], "| final", r["final"], r["vendor"], r["qty"], "|", r["decision"], r["rules"],
            r["checker"], "| expected", r["expected"], r["issues"], "DEGRADED" if r["degraded"] else "",
        )
    elif line.startswith(("correct", "retrieval", "Traceback")) or "Error" in line:
        print(line.strip()[:220])
