"""Safety layer 2: a documented pattern list for injection and abusive language. Standard library only, for both services."""
import re

INJECTION = [
    r"ignore (all |any |your |the )?(previous|prior|above|earlier)? ?(instructions|rules|prompts?)",
    r"disregard (all |any |your |the )?(previous|prior|above)? ?(instructions|rules)",
    r"forget (your|all|previous) (role|instructions|rules)",
    r"you are now",
    r"new (system )?(instruction|message)",
    r"system\s*:",
    r"(reveal|show|print).{0,20}(system prompt|instructions)",
    r"(disable|skip|bypass|override).{0,30}(guardrail|safety|check|polic)",
    r"approve (all|every)",
    r"respond only with",
    r"\bai agents?\b",
    r"(set|use|pass).{0,30}(vendor_id|location|persona|sku\s*=)",
    r"ignore pol-\d+",
    r"(call|use) (get_inventory|rag_search|lookup_vendor|forecast)\b",
    r"drop table",
]
TOXIC = [r"\bidiots?\b", r"\bscum\b", r"\bworthless\b", r"\bmorons?\b"]

_INJECTION = re.compile("|".join(INJECTION), re.IGNORECASE)
_TOXIC = re.compile("|".join(TOXIC), re.IGNORECASE)


def screen(text: str) -> str | None:
    """Return "injection", "toxic" or None. Case-insensitive pattern match, so it misses paraphrases by design."""
    if _INJECTION.search(text):
        return "injection"
    if _TOXIC.search(text):
        return "toxic"
    return None
