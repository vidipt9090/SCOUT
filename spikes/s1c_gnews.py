"""S1c: why does GNews report a total with no articles? Prints response bodies only, never the URL."""
import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["GNEWS_API_KEY"]
URL = "https://gnews.io/api/v4/search"


def show(label, params, headers=None):
    resp = httpx.get(URL, params=params, headers=headers or {}, timeout=30)
    body = resp.json()
    articles = body.get("articles", [])
    meta = {k: v for k, v in body.items() if k != "articles"}
    dates = sorted(a["publishedAt"][:10] for a in articles)
    print(label, resp.status_code, json.dumps(meta)[:300], "returned", len(articles), dates[:1], dates[-1:])
    if articles:
        print("  fields", sorted(articles[0]), "source", articles[0].get("source"))
        print("  content", repr((articles[0].get("content") or "")[:120]))
    time.sleep(1.5)


base = {"q": '"port strike"', "lang": "en", "max": 10}
show("header_key", base, {"X-Api-Key": KEY})
show("query_key", {**base, "apikey": KEY})
show("query_key_no_quotes", {**base, "q": "port strike", "apikey": KEY})
show("query_key_30d", {**base, "from": "2026-10-05T00:00:00Z", "to": "2026-10-29T00:00:00Z", "apikey": KEY})
show("query_key_2016", {**base, "from": "2016-05-01T00:00:00Z", "to": "2016-06-19T23:59:59Z", "apikey": KEY})
show("query_key_2025", {**base, "from": "2025-10-01T00:00:00Z", "to": "2025-10-31T23:59:59Z", "apikey": KEY})
