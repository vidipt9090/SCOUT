"""Live GNews fetch to a snapshot. The key goes in a header so it never reaches a URL, log or snapshot."""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

URL = "https://gnews.io/api/v4/search"
SNAPSHOT_DIR = Path("data/snapshots")
QUERIES = ["port congestion", "port strike", "shipping delay", "dockworkers strike", "typhoon port", "supply chain disruption"]
PAUSE_S = 2
RETRY_WAITS_S = (5, 15, 30)


def fetch_query(client: httpx.Client, query: str, key: str) -> list[dict]:
    for wait in RETRY_WAITS_S:
        resp = client.get(URL, params={"q": query, "lang": "en", "max": 10}, headers={"X-Api-Key": key})
        if resp.status_code != 429:
            break
        time.sleep(wait)
    resp.raise_for_status()
    body = resp.json()
    removed = body.get("articlesRemovedFromResponse")
    if removed:
        print(f"warning: GNews removed articles for {query!r}: {list(removed)}")
    return body.get("articles", [])


def main():
    load_dotenv()
    key = os.environ["GNEWS_API_KEY"]
    articles: dict[str, dict] = {}
    with httpx.Client(timeout=30) as client:
        for query in QUERIES:
            found = fetch_query(client, query, key)
            print(query, len(found))
            for a in found:
                articles[a["url"]] = a
            time.sleep(PAUSE_S)
    now = datetime.now(timezone.utc)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"gnews_{now:%Y%m%dT%H%M%SZ}.json"
    path.write_text(
        json.dumps({"fetched_at": now.isoformat(), "queries": QUERIES, "articles": list(articles.values())}, indent=1),
        encoding="utf-8",
    )
    print("wrote", path, "articles", len(articles))


if __name__ == "__main__":
    main()
