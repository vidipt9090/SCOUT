"""Rebuild the ChromaDB collection from data/synth/documents.jsonl."""
import json
from pathlib import Path

import chromadb

ROOT = Path(__file__).parents[2]
INDEX_DIR = ROOT / "data/rag/chroma"
COLLECTION = "scout_docs"


def main():
    chunks = [
        json.loads(line)
        for line in (ROOT / "data/synth/documents.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    col = client.create_collection(COLLECTION)
    col.add(
        ids=[c["chunk_id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{k: c[k] for k in ("doc_id", "doc_class", "sku", "vendor_id", "persona_scope")} for c in chunks],
    )
    print("indexed", col.count())


if __name__ == "__main__":
    main()
