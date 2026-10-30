"""Retrieval probe, two parts.

1. 15 queries with known correct documents: hit rate and precision at 5. Precision has a ceiling, because a
   query may have fewer than 5 relevant chunks in scope, so the ceiling is reported beside it.
2. One query per procedure cell: is the exact clause for that disruption type and severity in the top 5?
   This is what the Planner depends on.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from data.rag.retrieve import collection, search  # noqa: E402
from data.synth.build_docs import TYPE_NAMES  # noqa: E402

K = 5
PLANT_SOP = "SOP-DISRUPTION-PLANT"
RETAIL_SOP = "SOP-DISRUPTION-RETAIL-DC"
QUERIES = [
    ("what should the plant do about a severity 2 port delay", "plant", "FOODS_3_363", [PLANT_SOP]),
    ("plant procedure for a labour strike at severity 3", "plant", "FOODS_3_363", [PLANT_SOP]),
    ("plant procedure when a major corridor is closed", "plant", "HOBBIES_1_048", [PLANT_SOP]),
    ("retail DC procedure for a local weather disruption", "retail_dc", "FOODS_3_363", [RETAIL_SOP]),
    ("retail DC procedure for a severity 3 strike", "retail_dc", "HOBBIES_1_048", [RETAIL_SOP]),
    ("systemic disruption with no alternate, who decides", "plant", "FOODS_3_363", [PLANT_SOP]),
    ("how much cover must a donor keep after a stock transfer", "retail_dc", "FOODS_3_363", ["SOP-TRANSFER", "POL-06"]),
    ("can a plant receive a stock transfer", "retail_dc", "FOODS_3_363", ["SOP-TRANSFER", "POL-06"]),
    ("purchase order above the finance limit", "plant", "FOODS_3_363", ["SOP-ESCALATION", "POL-04"]),
    ("how many source domains are needed at severity 4", "plant", "FOODS_3_363", ["SOP-ESCALATION", "POL-07"]),
    ("are tier 3 vendors allowed for critical items", "plant", "FOODS_3_076", ["POL-03"]),
    ("safety stock minimum days of supply", "plant", "FOODS_3_363", ["POL-02"]),
    ("emergency order limit above baseline volume", "retail_dc", "FOODS_3_363", ["POL-01"]),
    ("feed text instructing an action", "plant", "FOODS_3_363", ["POL-08"]),
]


def load_chunks():
    lines = (ROOT / "data/synth/documents.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines]


def in_scope(chunk, persona, sku):
    return chunk["persona_scope"] in (persona, "all") and chunk["sku"] in (sku, "all")


def main():
    col = collection()
    chunks = load_chunks()
    contracts = sorted({c["doc_id"] for c in chunks if c["sku"] == "FOODS_3_363"})
    queries = QUERIES + [("lead time and minimum order quantity for this item", "plant", "FOODS_3_363", contracts)]
    assert len(queries) == 15

    hits, precision, ceiling = 0, 0.0, 0.0
    for query, persona, sku, relevant in queries:
        n_relevant = sum(r["doc_id"] in relevant for r in search(col, query, persona, sku, K))
        available = sum(c["doc_id"] in relevant and in_scope(c, persona, sku) for c in chunks)
        hits += n_relevant > 0
        precision += n_relevant / K
        ceiling += min(available, K) / K
        print(f"{'HIT ' if n_relevant else 'MISS'} {n_relevant}/{K} {query}")
    n = len(queries)
    print(f"hit_rate_at_5 {hits / n:.2f}  precision_at_5 {precision / n:.2f}  ceiling {ceiling / n:.2f}")

    found, total = 0, 0
    for persona, name, doc_id in (("plant", "Plant", PLANT_SOP), ("retail_dc", "Retail DC", RETAIL_SOP)):
        for severity in (2, 3, 4):
            for dtype, dname in TYPE_NAMES.items():
                query = f"{name} procedure for {dname} at severity {severity}"
                band = f"severity {severity}" if severity != 2 else "severity 1 or 2"
                wanted = [c["chunk_id"] for c in chunks
                          if c["doc_id"] == doc_id and dname in c["text"] and band in c["text"]]
                assert len(wanted) == 1, query
                top = [r["chunk_id"] for r in search(col, query, persona, "FOODS_3_363", K)]
                total += 1
                found += wanted[0] in top
                if wanted[0] not in top:
                    print("EXACT MISS", query)
    print(f"exact_clause_in_top_5 {found}/{total}")


if __name__ == "__main__":
    main()
