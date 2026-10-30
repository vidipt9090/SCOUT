"""S1: one live newsdata.io call saved as a snapshot, then replayed with no network. The key goes in a header, never a URL."""
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
SNAPSHOT = Path("data/snapshots/s1_spike.json")

resp = httpx.get(
    "https://newsdata.io/api/1/latest",
    params={"q": "port strike", "language": "en"},
    headers={"X-ACCESS-KEY": os.environ["NEWSDATA_API_KEY"]},
    timeout=30,
)
print("status", resp.status_code)
print("rate headers", {k: v for k, v in resp.headers.items() if "limit" in k.lower() or "credit" in k.lower()})
body = resp.json()
print("api status", body.get("status"), "totalResults", body.get("totalResults"), "count", len(body.get("results", [])))
if resp.status_code != 200:
    print("error body", json.dumps(body)[:300])
    raise SystemExit(1)

SNAPSHOT.write_text(
    json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat(), "response": body}, indent=1),
    encoding="utf-8",
)

first = body["results"][0]
print("fields", sorted(first))
now = datetime.now(timezone.utc)
ages = [
    (now - datetime.fromisoformat(r["pubDate"]).replace(tzinfo=timezone.utc)).total_seconds() / 3600
    for r in body["results"]
    if r.get("pubDate")
]
print("newest article age hours", round(min(ages), 1))
for field in ("description", "content", "source_id", "source_url", "pubDate"):
    print(field, repr(str(first.get(field))[:70]))


def blocked(*args, **kwargs):
    raise OSError("network disabled for replay")


socket.socket.connect = blocked
replayed = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
print("S1 replay offline ok, articles", len(replayed["response"]["results"]))
