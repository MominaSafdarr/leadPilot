import json
import chromadb
from pathlib import Path
from collections import Counter

INPUT_FILES = {
    "llm_top10": "data/owasp/llm_top10_structured.json",
    "agentic_top10": "data/owasp/agentic_top10_structured.json",
}

SUB_CHUNK_WORD_LIMIT = 200
SUB_CHUNK_OVERLAP = 40

chroma_client = chromadb.PersistentClient(path="./chroma_data")

# Start fresh each run so re-running doesn't leave stale/duplicate chunks
try:
    chroma_client.delete_collection(name="owasp_risks")
except Exception:
    pass
collection = chroma_client.create_collection(name="owasp_risks")


def sub_chunk_if_needed(text):
    """Only splits sections that exceed the word limit. Short ones pass
    through untouched as a single chunk. Long ones become overlapping
    pieces so no idea gets sliced cleanly in half at a boundary."""
    words = text.split()
    if len(words) <= SUB_CHUNK_WORD_LIMIT:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + SUB_CHUNK_WORD_LIMIT
        chunks.append(" ".join(words[start:end]))
        start += SUB_CHUNK_WORD_LIMIT - SUB_CHUNK_OVERLAP
    return chunks


def main():
    documents, metadatas, ids = [], [], []
    doc_id = 0
    sections_per_taxonomy = Counter()

    for taxonomy, path in INPUT_FILES.items():
        with open(path, "r", encoding="utf-8") as f:
            sections = json.load(f)

        sections_per_taxonomy[taxonomy] = len(sections)

        for section in sections:
            pieces = sub_chunk_if_needed(section["text"])
            for piece in pieces:
                if not piece.strip():
                    continue
                documents.append(piece)
                metadatas.append({
                    "taxonomy": taxonomy,
                    "category": section["category"],
                    "subsection": section["subsection"],
                })
                ids.append(f"{taxonomy}_{doc_id}")
                doc_id += 1

    # Chroma embeds each document automatically using its default local
    # model (all-MiniLM-L6-v2, downloaded once on first run) — no API calls
    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"Indexed {len(documents)} chunks total\n")

    print("Source sections per taxonomy:")
    for taxonomy, count in sections_per_taxonomy.items():
        print(f"  {taxonomy}: {count} sections")

    print("\nChunks per taxonomy (after sub-chunking long sections):")
    tax_counts = Counter(m["taxonomy"] for m in metadatas)
    for taxonomy, count in tax_counts.items():
        print(f"  {taxonomy}: {count} chunks")

    print("\nChunks per subsection type:")
    sub_counts = Counter(m["subsection"] for m in metadatas)
    for subsection, count in sub_counts.most_common():
        print(f"  {subsection}: {count}")

    print(f"\nCollection '{collection.name}' now holds {collection.count()} chunks.")


if __name__ == "__main__":
    main()