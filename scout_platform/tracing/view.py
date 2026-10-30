"""Render one run as a static HTML timeline: agents, tools, guardrail events, provenance and the final plan."""
import html
import json
import sys
from datetime import datetime
from pathlib import Path

from scout_platform.tracing.summary import load_events

STYLE = """
body{font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1000px;padding:24px 16px;color:#1c2024;background:#fff}
table{border-collapse:collapse;width:100%;margin:12px 0 24px}
th,td{border-bottom:1px solid #d9dde1;padding:6px 8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:#f3f5f6}.adk{color:#0b5cad}.crewai{color:#7a3e9d}
tr.guard{background:#fff4d6}tr.err{background:#fde4e4}
@media (prefers-color-scheme:dark){body{background:#15181b;color:#e7e9ec}th{background:#23282d}
th,td{border-color:#353b42}tr.guard{background:#4a3a0c}tr.err{background:#532222}.adk{color:#74b3f2}.crewai{color:#cd9de8}}
"""


def e(value) -> str:
    return html.escape("" if value is None else str(value))


def table(headers: list[str], rows: list[list]) -> str:
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def timeline(events: list[dict]) -> str:
    start = datetime.fromisoformat(events[0]["ts_wall"])
    rows = []
    for ev in events:
        offset = (datetime.fromisoformat(ev["ts_wall"]) - start).total_seconds()
        kind = ev["event_type"]
        cls = "guard" if kind == "guardrail" else "err" if kind == "error" else ""
        detail = ev["error"] or ev["payload_ref"] or ""
        tokens = f"{ev['tokens_in']}/{ev['tokens_out']}" if ev["tokens_in"] else ""
        rows.append(
            f'<tr class="{cls}"><td>{offset:.1f}</td><td class="{e(ev["framework"])}">{e(ev["framework"])}</td>'
            f"<td>{e(ev['agent'])}</td><td>{e(kind)}</td><td>{e(ev['tool_name'])}</td><td>{e(tokens)}</td>"
            f"<td>{e(ev['prompt_version'])}</td><td>{e(detail)}</td></tr>"
        )
    head = "".join(f"<th>{h}</th>" for h in ("s", "framework", "agent", "event", "tool or layer", "tokens in/out", "prompt", "detail"))
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def render(run_id: str, root: Path = Path("runs")) -> Path:
    record = json.loads((root / "records" / f"{run_id}.json").read_text(encoding="utf-8"))
    result = json.loads((root / "records" / f"{run_id}.result.json").read_text(encoding="utf-8"))
    events = load_events(record["trace_path"])
    assessment = result.get("assessment") or {}
    plan = result.get("plan") or {}
    verdict = result.get("verdict") or {}
    chosen = verdict.get("counter_plan") or plan
    parts = [
        f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Run {e(run_id)}</title><style>{STYLE}</style></head><body><h1>Run {e(run_id)}</h1>",
        table(["Field", "Value"], [
            *[[k, v] for k, v in record["condition"].items()],
            ["Outcome", record["outcome"]], ["Degraded", record["degraded"]],
            ["Total latency (s)", record["total_latency_s"]], ["Tokens in/out", f"{record['tokens_in']}/{record['tokens_out']}"],
            ["Estimated cost (USD)", record["estimated_cost"]],
        ]),
        "<h2>Decision</h2>",
        table(["Field", "Value"], [
            ["Severity (votes)", f"{assessment.get('severity')} {assessment.get('severity_votes')}"],
            ["Source domains", ", ".join(assessment.get("corroborating_domains", []))],
            ["Proposed action", plan.get("action")], ["Verdict", verdict.get("decision")],
            ["Rules violated", ", ".join(verdict.get("violated_rules", []))], ["Checker", verdict.get("checker")],
            ["Final action", chosen.get("action")], ["Vendor or donor", chosen.get("vendor_id")],
            ["Quantity", chosen.get("quantity")], ["Rationale", chosen.get("rationale")], ["Reasons", verdict.get("reasons")],
        ]),
        "<h2>Provenance</h2>",
        table(["Kind", "Ids"], [
            ["Signals", ", ".join(assessment.get("supporting_signal_ids", []))],
            ["Documents cited", ", ".join(chosen.get("cited_doc_ids", []))],
        ]),
        "<h2>Timeline</h2>", timeline(events), "</body></html>",
    ]
    out = root / "reports" / f"{run_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(parts), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(render(sys.argv[1]))
