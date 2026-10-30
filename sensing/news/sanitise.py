"""Ingestion sanitiser, safety layer 1: strip HTML, cap length, extract the domain, wrap text as quoted data."""
import hashlib
import html
import re
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict

MAX_HEADLINE = 200
MAX_SNIPPET = 500
OPEN = "<<<FEED_DATA"
CLOSE = "FEED_DATA>>>"

_BLOCKS = re.compile(r"<(script|style)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_TAGS = re.compile(r"<[^>]*>")
_SPACE = re.compile(r"\s+")


class FeedItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item_id: str
    source_domain: str
    headline: str
    snippet: str
    published_at: str


def clean(text: str | None, cap: int) -> str:
    text = _TAGS.sub(" ", _BLOCKS.sub(" ", html.unescape(text or "")))
    # A feed item must not be able to close its own quotation.
    text = text.replace(OPEN, " ").replace(CLOSE, " ").replace("<<<", " ").replace(">>>", " ")
    return _SPACE.sub(" ", text).strip()[:cap]


def domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host.removeprefix("www.")


def make_item(url: str, headline: str | None, snippet: str | None, published_at: str) -> FeedItem:
    domain = domain_of(url)
    if not domain:
        raise ValueError(f"no domain in source url: {url!r}")
    return FeedItem(
        item_id="itm-" + hashlib.sha256(f"{domain}|{headline}".encode()).hexdigest()[:12],
        source_domain=domain,
        headline=clean(headline, MAX_HEADLINE),
        snippet=clean(snippet, MAX_SNIPPET),
        published_at=published_at,
    )


def wrap_as_data(item: FeedItem) -> str:
    """Render an item for a prompt. Everything between the markers is untrusted data, never instructions."""
    return (
        f"{OPEN} id={item.item_id} domain={item.source_domain}\n"
        f"headline: {item.headline}\nsnippet: {item.snippet}\n{CLOSE}"
    )
