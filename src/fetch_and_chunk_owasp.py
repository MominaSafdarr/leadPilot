import re
import requests
import json
from pathlib import Path
from pypdf import PdfReader

DATA_DIR = Path("data/owasp")
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "llm_top10": {
        "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf",
        "category_pattern": r"(LLM\d{2}:2025[^\n]*)",
    },
    "agentic_top10": {
        "url": "https://genai.owasp.org/download/52117",
        "category_pattern": r"(ASI\d{2}[^\n]*)",
    },
}

CHUNK_WORD_SIZE = 250
CHUNK_OVERLAP = 50


def download_pdf(url, save_path):
    headers = {"User-Agent": "Mozilla/5.0"}  # some sites block the default requests UA
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    save_path.write_bytes(resp.content)


def extract_text(pdf_path):
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def split_by_category(full_text, pattern):
    """Splits the full document into sections, one per category header,
    using the header text itself as the split point."""
    parts = re.split(pattern, full_text)
    # re.split with a capturing group returns alternating [text, header, text, header, ...]
    sections = []
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append((header, body))
    return sections


def chunk_text(text, chunk_size=CHUNK_WORD_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def main():
    all_chunks = []

    for taxonomy, config in SOURCES.items():
        pdf_path = DATA_DIR / f"{taxonomy}.pdf"
        print(f"\nDownloading {taxonomy}...")
        download_pdf(config["url"], pdf_path)

        print(f"Extracting text from {pdf_path}...")
        full_text = extract_text(pdf_path)
        print(f"  {len(full_text)} characters extracted")

        sections = split_by_category(full_text, config["category_pattern"])
        print(f"  Found {len(sections)} category sections")

        for header, body in sections:
            chunks = chunk_text(body)
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "taxonomy": taxonomy,
                    "category": header,
                    "chunk_index": i,
                    "text": chunk,
                })
            print(f"    {header}: {len(chunks)} chunks")

    output_path = DATA_DIR / "owasp_chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nDone. {len(all_chunks)} total chunks saved to {output_path}")
    print("\n--- Sample chunk ---")
    print(json.dumps(all_chunks[0], indent=2)[:800])


if __name__ == "__main__":
    main()