# S1 News

Source changed from newsdata.io to GNews on 2026-10-30 at the project owner's request, with the aim of matching news to M5 dates. Testing showed GNews cannot do that. It is kept as the source of current real news.

Result: pass for current news, fail for M5-era news. The newsdata.io call, snapshot and offline replay passed. The GNews call, snapshot and offline replay passed in B2.8 (29 articles from 22 domains).

## GNews findings (live tests with the free key, and gnews.io docs and pricing, 2026-10-30)

| Window | Result |
|---|---|
| 2016-05-01 to 2016-06-19 | `totalArticles` 0 |
| 2025-10 | 1 article counted, then removed by the plan |
| Recent, `port strike` | 2804 counted, 10 returned, dated 2026-10-16 to 2026-10-28 |

- Free plan: 100 requests a day, up to 10 articles per request, last 30 days, 12-hour delay, truncated `content`, non-commercial use only.
- Paid plans start at EUR 49.99 a month and reach back only to 2020, so no plan covers M5 (sales 2011 to May 2016).
- Older articles are removed silently: the call returns 200, a `totalArticles` count, no articles, and an `articlesRemovedFromResponse` field. The news client must check that field.
- A quoted query with `from` and `to` inside the 30-day window returned 0, while the same words unquoted returned articles. Use unquoted queries.
- The `X-Api-Key` header works. The docs show only `apikey` in the query string. Use the header so the key stays out of URLs and logs.
- `source.url` gives the domain for corroboration.
- Rapid calls return 429. The fetcher pauses 2 s between queries and retries with backoff.

Redistribution terms are not confirmed, so snapshots stay git-ignored. A fresh clone therefore needs `make news-snapshot` and a key.

## Consequence for M5

News dates and sales dates cannot align with GNews. The run treats the last M5 sales day as simulated today, and news text comes from replayed snapshots plus planted scenario items.
