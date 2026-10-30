"""Offline feeds: saved GNews snapshots, planted scenario items and poison items. All pass through the sanitiser."""
import json
from pathlib import Path

import yaml

from sensing.news.sanitise import FeedItem, make_item

SNAPSHOT_DIR = Path("data/snapshots")
SCENARIOS = Path("data/scenarios")
PLANTED_DATE = "2016-05-21T09:00:00Z"  # the day before simulated today


def replay_snapshot(path: Path | None = None) -> list[FeedItem]:
    path = path or sorted(SNAPSHOT_DIR.glob("gnews_*.json"))[-1]
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    return [
        make_item(a["source"]["url"], a.get("title"), a.get("description"), a["publishedAt"])
        for a in snapshot["articles"]
    ]


def _items(entries: list[dict]) -> list[FeedItem]:
    return [make_item(f"https://{e['domain']}/", e["headline"], e["snippet"], PLANTED_DATE) for e in entries]


def planted(scenario_id: str) -> list[FeedItem]:
    data = yaml.safe_load((SCENARIOS / "planted.yaml").read_text(encoding="utf-8"))
    return _items(data[scenario_id])


def poison() -> list[FeedItem]:
    data = yaml.safe_load((SCENARIOS / "poison.yaml").read_text(encoding="utf-8"))
    return _items(data["items"])
