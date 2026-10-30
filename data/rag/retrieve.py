"""Retrieval over the Chroma index. Metadata filters narrow to persona and SKU before similarity."""
from pathlib import Path

import chromadb

ROOT = Path(__file__).parents[2]
INDEX_DIR = ROOT / "data/rag/chroma"
COLLECTION = "scout_docs"


def collection():
    return chromadb.PersistentClient(path=str(INDEX_DIR)).get_collection(COLLECTION)


def search(col, query: str, persona: str, sku: str, k: int = 5) -> list[dict]:
    where = {"$and": [{"persona_scope": {"$in": [persona, "all"]}}, {"sku": {"$in": [sku, "all"]}}]}
    found = col.query(query_texts=[query], n_results=k, where=where)
    return [
        {"chunk_id": cid, "doc_id": meta["doc_id"], "doc_class": meta["doc_class"], "text": text, "distance": dist}
        for cid, meta, text, dist in zip(
            found["ids"][0], found["metadatas"][0], found["documents"][0], found["distances"][0]
        )
    ]
