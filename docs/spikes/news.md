# S1 News

Result: pass. One live call to `https://newsdata.io/api/1/latest` with the key in the `X-ACCESS-KEY` header was saved as a snapshot and replayed with sockets disabled.

Free-plan findings from the live response:
- 10 articles per call. A daily credit counter of 200 was reported (`x-api-limit-remaining: 199` after one call).
- A rate-limit header of 60 was reported. Its time window was not confirmed.
- The newest article was about 12 hours old, consistent with a delay on the free plan.
- `content` returns "ONLY AVAILABLE IN PAID PLANS". The Signal `snippet` must use `description`.
- `source_id` and `source_url` are available for corroborating domains.

Redistribution terms are not confirmed, so snapshots are git-ignored for now. A fresh clone therefore needs `make news-snapshot` and a key.
