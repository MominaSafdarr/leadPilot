# # # # # # # # # from pdfminer.high_level import extract_text_to_fp
# # # # # # # # # from pdfminer.layout import LAParams
# # # # # # # # # from bs4 import BeautifulSoup
# # # # # # # # # from io import BytesIO
# # # # # # # # # import re
# # # # # # # # # from collections import Counter

# # # # # # # # # def pdf_to_html(pdf_path):
# # # # # # # # #     output = BytesIO()
# # # # # # # # #     with open(pdf_path, "rb") as f:
# # # # # # # # #         extract_text_to_fp(f, output, laparams=LAParams(), output_type="html", codec="utf-8")
# # # # # # # # #     return output.getvalue().decode("utf-8")

# # # # # # # # # html_content = pdf_to_html("data/owasp/llm_top10.pdf")
# # # # # # # # # soup = BeautifulSoup(html_content, "html.parser")
# # # # # # # # # spans = soup.find_all("span")

# # # # # # # # # pattern = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")

# # # # # # # # # style_counts = Counter()
# # # # # # # # # style_samples = {}

# # # # # # # # # for span in spans:
# # # # # # # # #     style = span.get("style", "")
# # # # # # # # #     match = pattern.search(style)
# # # # # # # # #     if not match:
# # # # # # # # #         continue
# # # # # # # # #     family = match.group(1).strip()
# # # # # # # # #     size = round(float(match.group(2)))
# # # # # # # # #     text = span.get_text().strip()
# # # # # # # # #     if not text:
# # # # # # # # #         continue

# # # # # # # # #     key = (family, size)
# # # # # # # # #     style_counts[key] += 1
# # # # # # # # #     if key not in style_samples:
# # # # # # # # #         style_samples[key] = []
# # # # # # # # #     if len(style_samples[key]) < 3:
# # # # # # # # #         style_samples[key].append(text[:60])

# # # # # # # # # print(f"Total matching spans: {sum(style_counts.values())}\n")
# # # # # # # # # print("Font family + size combos, most common first:\n")
# # # # # # # # # for (family, size), count in style_counts.most_common():
# # # # # # # # #     samples = " | ".join(style_samples[(family, size)])
# # # # # # # # #     print(f"{family}, {size}px  (count={count})  samples: {samples}")

# # # # # # # # from pdfminer.high_level import extract_text_to_fp
# # # # # # # # from pdfminer.layout import LAParams
# # # # # # # # from bs4 import BeautifulSoup
# # # # # # # # from io import BytesIO
# # # # # # # # import re, json
# # # # # # # # from pathlib import Path

# # # # # # # # PDF_PATH = "data/owasp/llm_top10.pdf"
# # # # # # # # OUTPUT_JSON = "data/owasp/llm_top10_structured.json"

# # # # # # # # CATEGORY_STYLE = ("BarlowBold", 24)   # confirmed from real font analysis
# # # # # # # # CATEGORY_PATTERN = re.compile(r"^LLM\d{2}:2025")

# # # # # # # # SUBSECTION_NAMES = {
# # # # # # # #     "Description",
# # # # # # # #     "Common Examples of Vulnerability",
# # # # # # # #     "Types of Prompt Injection Vulnerabilities",
# # # # # # # #     "Prevention and Mitigation Strategies",
# # # # # # # #     "Example Attack Scenarios",
# # # # # # # #     "Reference Links",
# # # # # # # #     "Related Frameworks and Taxonomies",
# # # # # # # # }

# # # # # # # # STYLE_PATTERN = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")


# # # # # # # # def pdf_to_html(pdf_path):
# # # # # # # #     output = BytesIO()
# # # # # # # #     with open(pdf_path, "rb") as f:
# # # # # # # #         extract_text_to_fp(f, output, laparams=LAParams(), output_type="html", codec="utf-8")
# # # # # # # #     return output.getvalue().decode("utf-8")


# # # # # # # # def get_style(span):
# # # # # # # #     match = STYLE_PATTERN.search(span.get("style", ""))
# # # # # # # #     if not match:
# # # # # # # #         return None
# # # # # # # #     return (match.group(1).strip(), round(float(match.group(2))))


# # # # # # # # def main():
# # # # # # # #     html_content = pdf_to_html(PDF_PATH)
# # # # # # # #     soup = BeautifulSoup(html_content, "html.parser")
# # # # # # # #     spans = soup.find_all("span")

# # # # # # # #     structured = []
# # # # # # # #     current_category, current_subsection = None, "Description"
# # # # # # # #     buffer = []
# # # # # # # #     skipped_garbled = 0

# # # # # # # #     def flush():
# # # # # # # #         if current_category and buffer:
# # # # # # # #             structured.append({
# # # # # # # #                 "category": current_category,
# # # # # # # #                 "subsection": current_subsection,
# # # # # # # #                 "text": " ".join(buffer).strip(),
# # # # # # # #             })

# # # # # # # #     for span in spans:
# # # # # # # #         style = get_style(span)
# # # # # # # #         text = span.get_text().strip()
# # # # # # # #         if not text:
# # # # # # # #             continue
# # # # # # # #         if "(cid:" in text:
# # # # # # # #             skipped_garbled += 1
# # # # # # # #             continue

# # # # # # # #         # New category heading
# # # # # # # #         if style == CATEGORY_STYLE and CATEGORY_PATTERN.match(text):
# # # # # # # #             flush(); buffer = []
# # # # # # # #             current_category = text
# # # # # # # #             current_subsection = "Description"
# # # # # # # #             continue

# # # # # # # #         # New subsection within current category
# # # # # # # #         if text in SUBSECTION_NAMES:
# # # # # # # #             flush(); buffer = []
# # # # # # # #             current_subsection = text
# # # # # # # #             continue

# # # # # # # #         if current_category:
# # # # # # # #             buffer.append(text)
# # # # # # # #     flush()

# # # # # # # #     Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
# # # # # # # #     with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
# # # # # # # #         json.dump(structured, f, indent=2)

# # # # # # # #     categories_found = sorted(set(s["category"] for s in structured))
# # # # # # # #     print(f"Categories found ({len(categories_found)}): {categories_found}")
# # # # # # # #     print(f"Total sections extracted: {len(structured)}")
# # # # # # # #     print(f"Skipped {skipped_garbled} garbled (cid:) spans")
# # # # # # # #     print(f"\nSaved to {OUTPUT_JSON}")
# # # # # # # #     print("\n--- Sample section ---")
# # # # # # # #     print(json.dumps(structured[5], indent=2)[:600])


# # # # # # # # if __name__ == "__main__":
# # # # # # # #     main()

# # # # # # # from pdfminer.high_level import extract_text_to_fp
# # # # # # # from pdfminer.layout import LAParams
# # # # # # # from bs4 import BeautifulSoup
# # # # # # # from io import BytesIO
# # # # # # # import re

# # # # # # # PDF_PATH = "data/owasp/llm_top10.pdf"
# # # # # # # STYLE_PATTERN = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")

# # # # # # # def pdf_to_html(pdf_path):
# # # # # # #     output = BytesIO()
# # # # # # #     with open(pdf_path, "rb") as f:
# # # # # # #         extract_text_to_fp(f, output, laparams=LAParams(), output_type="html", codec="utf-8")
# # # # # # #     return output.getvalue().decode("utf-8")

# # # # # # # def get_style(span):
# # # # # # #     match = STYLE_PATTERN.search(span.get("style", ""))
# # # # # # #     if not match:
# # # # # # #         return None
# # # # # # #     return (match.group(1).strip(), round(float(match.group(2))))

# # # # # # # html_content = pdf_to_html(PDF_PATH)
# # # # # # # soup = BeautifulSoup(html_content, "html.parser")
# # # # # # # spans = soup.find_all("span")

# # # # # # # print("Every span containing 'LLM04':\n")
# # # # # # # for i, span in enumerate(spans):
# # # # # # #     text = span.get_text().strip()
# # # # # # #     if "LLM04" in text or "Poisoning" in text:
# # # # # # #         style = get_style(span)
# # # # # # #         print(f"[index {i}] style={style}  text={text!r}")


# # # # # # from pdfminer.high_level import extract_text_to_fp
# # # # # # from pdfminer.layout import LAParams
# # # # # # from bs4 import BeautifulSoup
# # # # # # from io import BytesIO
# # # # # # import requests, re, json
# # # # # # from pathlib import Path
# # # # # # from collections import Counter

# # # # # # PDF_URL = "https://genai.owasp.org/download/52117"
# # # # # # PDF_PATH = "data/owasp/agentic_top10.pdf"
# # # # # # OUTPUT_JSON = "data/owasp/agentic_top10_structured.json"

# # # # # # CATEGORY_PATTERN = re.compile(r"^ASI\d{2}")
# # # # # # STYLE_PATTERN = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")

# # # # # # # Best guesses at likely subsection labels for this document, based on
# # # # # # # third-party summaries of its content — NOT confirmed from the real PDF
# # # # # # # yet. The diagnostic output below will tell us if these are wrong.
# # # # # # CANDIDATE_SUBSECTIONS = {
# # # # # #     "Description", "Impact", "Mitigations", "Mitigation",
# # # # # #     "Examples", "Example Attack Scenarios", "Related Techniques",
# # # # # #     "Reference Links", "References",
# # # # # # }


# # # # # # def download_pdf():
# # # # # #     if Path(PDF_PATH).exists():
# # # # # #         return
# # # # # #     Path(PDF_PATH).parent.mkdir(parents=True, exist_ok=True)
# # # # # #     resp = requests.get(PDF_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
# # # # # #     resp.raise_for_status()
# # # # # #     Path(PDF_PATH).write_bytes(resp.content)


# # # # # # def pdf_to_html(pdf_path):
# # # # # #     output = BytesIO()
# # # # # #     with open(pdf_path, "rb") as f:
# # # # # #         extract_text_to_fp(f, output, laparams=LAParams(), output_type="html", codec="utf-8")
# # # # # #     return output.getvalue().decode("utf-8")


# # # # # # def get_style(span):
# # # # # #     match = STYLE_PATTERN.search(span.get("style", ""))
# # # # # #     if not match:
# # # # # #         return None
# # # # # #     return (match.group(1).strip(), round(float(match.group(2))))


# # # # # # def main():
# # # # # #     print("Downloading PDF...")
# # # # # #     download_pdf()

# # # # # #     print("Converting to HTML...")
# # # # # #     html_content = pdf_to_html(PDF_PATH)
# # # # # #     soup = BeautifulSoup(html_content, "html.parser")
# # # # # #     spans = soup.find_all("span")

# # # # # #     # --- DIAGNOSTIC: find style(s) used by real ASI category headings ---
# # # # # #     category_style_counts = Counter()
# # # # # #     category_samples = {}
# # # # # #     for span in spans:
# # # # # #         text = span.get_text().strip()
# # # # # #         if CATEGORY_PATTERN.match(text):
# # # # # #             style = get_style(span)
# # # # # #             if style:
# # # # # #                 category_style_counts[style] += 1
# # # # # #                 category_samples.setdefault(style, []).append(text[:60])

# # # # # #     print("\n--- Styles matching 'ASI##' pattern ---")
# # # # # #     for style, count in category_style_counts.most_common():
# # # # # #         print(f"  {style}: count={count}  samples={category_samples[style][:3]}")

# # # # # #     if not category_style_counts:
# # # # # #         print("\nNo ASI-pattern matches found at all — this PDF may use different")
# # # # # #         print("heading text than expected. Stopping here for inspection.")
# # # # # #         return

# # # # # #     # Heuristic: real headings should appear ~10 times (10 categories),
# # # # # #     # not dozens of times (which would indicate ToC/running-header noise)
# # # # # #     likely_style = min(category_style_counts, key=lambda s: abs(category_style_counts[s] - 10))
# # # # # #     print(f"\nAuto-selected heading style: {likely_style} (count={category_style_counts[likely_style]})")
# # # # # #     print("VERIFY this looks right above before trusting the extraction below.\n")

# # # # # #     # --- Also show any other bold/large spans we don't recognize, so we
# # # # # #     # can spot real subsection labels this script doesn't know about yet ---
# # # # # #     print("--- Other bold spans not matched as category or known subsection ---")
# # # # # #     unrecognized = Counter()
# # # # # #     for span in spans:
# # # # # #         text = span.get_text().strip()
# # # # # #         style = get_style(span)
# # # # # #         if not style or not text:
# # # # # #             continue
# # # # # #         if "bold" in style[0].lower() and text not in CANDIDATE_SUBSECTIONS and not CATEGORY_PATTERN.match(text):
# # # # # #             if len(text) < 50:  # skip long paragraph-like bold spans
# # # # # #                 unrecognized[text] += 1
# # # # # #     for text, count in unrecognized.most_common(15):
# # # # # #         print(f"  {count}x: {text!r}")

# # # # # #     # --- EXTRACTION using the auto-selected style ---
# # # # # #     structured = []
# # # # # #     current_category, current_subsection, buffer = None, "Description", []

# # # # # #     def flush():
# # # # # #         if current_category and buffer:
# # # # # #             structured.append({
# # # # # #                 "category": current_category,
# # # # # #                 "subsection": current_subsection,
# # # # # #                 "text": " ".join(buffer).strip(),
# # # # # #             })

# # # # # #     for span in spans:
# # # # # #         style = get_style(span)
# # # # # #         text = span.get_text().strip()
# # # # # #         if not text or "(cid:" in text:
# # # # # #             continue

# # # # # #         if style == likely_style and CATEGORY_PATTERN.match(text):
# # # # # #             flush(); buffer = []
# # # # # #             current_category, current_subsection = text, "Description"
# # # # # #             continue

# # # # # #         if text in CANDIDATE_SUBSECTIONS:
# # # # # #             flush(); buffer = []
# # # # # #             current_subsection = text
# # # # # #             continue

# # # # # #         if current_category:
# # # # # #             buffer.append(text)
# # # # # #     flush()

# # # # # #     Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
# # # # # #     with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
# # # # # #         json.dump(structured, f, indent=2)

# # # # # #     categories_found = sorted(set(s["category"] for s in structured))
# # # # # #     print(f"\n--- RESULT ---")
# # # # # #     print(f"Categories found ({len(categories_found)}): {categories_found}")
# # # # # #     print(f"Total sections extracted: {len(structured)}")
# # # # # #     print(f"Saved to {OUTPUT_JSON}")


# # # # # # if __name__ == "__main__":
# # # # # #     main()

# # # # # from pdfminer.high_level import extract_text_to_fp
# # # # # from pdfminer.layout import LAParams
# # # # # from bs4 import BeautifulSoup
# # # # # from io import BytesIO
# # # # # import requests, re, json
# # # # # from pathlib import Path
# # # # # from collections import Counter

# # # # # PDF_URL = "https://genai.owasp.org/download/52117"
# # # # # PDF_PATH = "data/owasp/agentic_top10.pdf"
# # # # # OUTPUT_JSON = "data/owasp/agentic_top10_structured.json"

# # # # # CATEGORY_PATTERN = re.compile(r"^ASI\d{2}")
# # # # # STYLE_PATTERN = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")

# # # # # CANDIDATE_SUBSECTIONS = {
# # # # #     "Description", "Impact", "Mitigations", "Mitigation",
# # # # #     "Examples", "Example Attack Scenarios", "Related Techniques",
# # # # #     "Reference Links", "References",
# # # # #     "Common Examples of the Vulnerability",   # confirmed real wording
# # # # #     "Prevention and Mitigation Guidelines",   # confirmed real wording
# # # # # }


# # # # # def download_pdf():
# # # # #     if Path(PDF_PATH).exists():
# # # # #         return
# # # # #     Path(PDF_PATH).parent.mkdir(parents=True, exist_ok=True)
# # # # #     resp = requests.get(PDF_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
# # # # #     resp.raise_for_status()
# # # # #     Path(PDF_PATH).write_bytes(resp.content)


# # # # # def pdf_to_html(pdf_path):
# # # # #     output = BytesIO()
# # # # #     with open(pdf_path, "rb") as f:
# # # # #         extract_text_to_fp(f, output, laparams=LAParams(), output_type="html", codec="utf-8")
# # # # #     return output.getvalue().decode("utf-8")


# # # # # def get_style(span):
# # # # #     match = STYLE_PATTERN.search(span.get("style", ""))
# # # # #     if not match:
# # # # #         return None
# # # # #     return (match.group(1).strip(), round(float(match.group(2))))


# # # # # def main():
# # # # #     print("Downloading PDF...")
# # # # #     download_pdf()

# # # # #     print("Converting to HTML...")
# # # # #     html_content = pdf_to_html(PDF_PATH)
# # # # #     soup = BeautifulSoup(html_content, "html.parser")
# # # # #     spans = soup.find_all("span")

# # # # #     category_style_counts = Counter()
# # # # #     category_samples = {}
# # # # #     for span in spans:
# # # # #         text = span.get_text().strip()
# # # # #         if CATEGORY_PATTERN.match(text):
# # # # #             style = get_style(span)
# # # # #             if style:
# # # # #                 category_style_counts[style] += 1
# # # # #                 category_samples.setdefault(style, []).append(text[:60])

# # # # #     print("\n--- Styles matching 'ASI##' pattern ---")
# # # # #     for style, count in category_style_counts.most_common():
# # # # #         print(f"  {style}: count={count}  samples={category_samples[style][:3]}")

# # # # #     if not category_style_counts:
# # # # #         print("\nNo ASI-pattern matches found — stopping for inspection.")
# # # # #         return

# # # # #     likely_style = min(category_style_counts, key=lambda s: abs(category_style_counts[s] - 10))
# # # # #     print(f"\nAuto-selected heading style: {likely_style} (count={category_style_counts[likely_style]})")

# # # # #     structured = []
# # # # #     current_category, current_subsection, buffer = None, "Description", []

# # # # #     def flush():
# # # # #         if current_category and buffer:
# # # # #             structured.append({
# # # # #                 "category": current_category,
# # # # #                 "subsection": current_subsection,
# # # # #                 "text": " ".join(buffer).strip(),
# # # # #             })

# # # # #     for span in spans:
# # # # #         style = get_style(span)
# # # # #         text = span.get_text().strip()
# # # # #         if not text or "(cid:" in text:
# # # # #             continue

# # # # #         if style == likely_style and CATEGORY_PATTERN.match(text):
# # # # #             flush(); buffer = []
# # # # #             current_category, current_subsection = text, "Description"
# # # # #             continue

# # # # #         if text in CANDIDATE_SUBSECTIONS:
# # # # #             flush(); buffer = []
# # # # #             current_subsection = text
# # # # #             continue

# # # # #         if current_category:
# # # # #             buffer.append(text)
# # # # #     flush()

# # # # #     Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
# # # # #     with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
# # # # #         json.dump(structured, f, indent=2)

# # # # #     categories_found = sorted(set(s["category"] for s in structured))
# # # # #     print(f"\n--- RESULT ---")
# # # # #     print(f"Categories found ({len(categories_found)}): {categories_found}")
# # # # #     print(f"Total sections extracted: {len(structured)}")

# # # # #     subsection_counts = Counter(s["subsection"] for s in structured)
# # # # #     print("\nSubsection distribution:")
# # # # #     for subsection, count in subsection_counts.most_common():
# # # # #         print(f"  {subsection}: {count}")

# # # # #     print(f"\nSaved to {OUTPUT_JSON}")


# # # # # if __name__ == "__main__":
# # # # #     main()

# # # # from pdfminer.high_level import extract_text_to_fp
# # # # from pdfminer.layout import LAParams
# # # # from bs4 import BeautifulSoup
# # # # from io import BytesIO
# # # # import requests, re
# # # # from pathlib import Path
# # # # from collections import Counter

# # # # PDF_URL = "https://genai.owasp.org/download/52117"
# # # # PDF_PATH = "data/owasp/agentic_top10.pdf"
# # # # HTML_PATH = "data/owasp/agentic_top10.html"

# # # # STYLE_PATTERN = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")


# # # # def download_pdf():
# # # #     if Path(PDF_PATH).exists():
# # # #         print(f"{PDF_PATH} already exists, skipping download")
# # # #         return
# # # #     Path(PDF_PATH).parent.mkdir(parents=True, exist_ok=True)
# # # #     resp = requests.get(PDF_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
# # # #     resp.raise_for_status()
# # # #     Path(PDF_PATH).write_bytes(resp.content)
# # # #     print(f"Downloaded {PDF_PATH} ({len(resp.content) / 1024:.0f} KB)")


# # # # def pdf_to_html(pdf_path):
# # # #     output = BytesIO()
# # # #     with open(pdf_path, "rb") as f:
# # # #         extract_text_to_fp(f, output, laparams=LAParams(), output_type="html", codec="utf-8")
# # # #     return output.getvalue().decode("utf-8")


# # # # def get_style(span):
# # # #     match = STYLE_PATTERN.search(span.get("style", ""))
# # # #     if not match:
# # # #         return None
# # # #     return (match.group(1).strip(), round(float(match.group(2))))


# # # # def main():
# # # #     download_pdf()

# # # #     print("Converting to HTML...")
# # # #     html_content = pdf_to_html(PDF_PATH)

# # # #     with open(HTML_PATH, "w", encoding="utf-8") as f:
# # # #         f.write(html_content)
# # # #     print(f"Saved HTML to {HTML_PATH}\n")

# # # #     soup = BeautifulSoup(html_content, "html.parser")
# # # #     spans = soup.find_all("span")

# # # #     style_counts = Counter()
# # # #     style_samples = {}

# # # #     for span in spans:
# # # #         style = get_style(span)
# # # #         text = span.get_text().strip()
# # # #         if not style or not text:
# # # #             continue
# # # #         style_counts[style] += 1
# # # #         style_samples.setdefault(style, [])
# # # #         if len(style_samples[style]) < 3:
# # # #             style_samples[style].append(text[:60].replace("\n", " "))

# # # #     print(f"Total styled spans: {sum(style_counts.values())}\n")
# # # #     print("Font family + size combos, most common first:\n")
# # # #     for style, count in style_counts.most_common():
# # # #         samples = " | ".join(style_samples[style])
# # # #         print(f"{style[0]}, {style[1]}px  (count={count})  samples: {samples}")


# # # # if __name__ == "__main__":
# # # #     main()

# # # from bs4 import BeautifulSoup
# # # import re

# # # HTML_PATH = "data/owasp/agentic_top10.html"
# # # STYLE_PATTERN = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")

# # # # Matches "ASI01: Agent Goal Hijack" — colon followed by a real title,
# # # # not a bare "ASI01:" reference inside body text
# # # FULL_HEADING_PATTERN = re.compile(r"^ASI\d{2}:\s*[A-Z]")


# # # def get_style(span):
# # #     match = STYLE_PATTERN.search(span.get("style", ""))
# # #     if not match:
# # #         return None
# # #     return (match.group(1).strip(), round(float(match.group(2))))


# # # with open(HTML_PATH, encoding="utf-8") as f:
# # #     soup = BeautifulSoup(f, "html.parser")

# # # spans = soup.find_all("span")

# # # print("Every span matching a full ASI heading pattern:\n")
# # # for span in spans:
# # #     text = span.get_text().strip()
# # #     if FULL_HEADING_PATTERN.match(text):
# # #         style = get_style(span)
# # #         print(f"{style}: {text[:80]!r}")

# # from bs4 import BeautifulSoup
# # import re, json
# # from pathlib import Path
# # from collections import Counter

# # HTML_PATH = "data/owasp/agentic_top10.html"
# # OUTPUT_JSON = "data/owasp/agentic_top10_structured.json"

# # CATEGORY_STYLE = ("Barlow-Regular", 14)   # confirmed from real heading scan
# # CATEGORY_PATTERN = re.compile(r"^ASI\d{2}:\s*[A-Z]")

# # SUBSECTION_NAMES = {
# #     "Description",
# #     "Common Examples of the Vulnerability",
# #     "Example Attack Scenarios",
# #     "Prevention and Mitigation Guidelines",
# #     "References",
# # }

# # STYLE_PATTERN = re.compile(r"font-family:\s*([^;]+);\s*font-size:([\d.]+)px")


# # def get_style(span):
# #     match = STYLE_PATTERN.search(span.get("style", ""))
# #     if not match:
# #         return None
# #     return (match.group(1).strip(), round(float(match.group(2))))


# # def main():
# #     with open(HTML_PATH, encoding="utf-8") as f:
# #         soup = BeautifulSoup(f, "html.parser")
# #     spans = soup.find_all("span")

# #     structured = []
# #     current_category, current_subsection, buffer = None, "Description", []

# #     def flush():
# #         if current_category and buffer:
# #             structured.append({
# #                 "category": current_category,
# #                 "subsection": current_subsection,
# #                 "text": " ".join(buffer).strip(),
# #             })

# #     for span in spans:
# #         style = get_style(span)
# #         text = span.get_text().strip()
# #         if not text or "(cid:" in text:
# #             continue

# #         if style == CATEGORY_STYLE and CATEGORY_PATTERN.match(text):
# #             flush(); buffer = []
# #             current_category, current_subsection = text, "Description"
# #             continue

# #         if text in SUBSECTION_NAMES:
# #             flush(); buffer = []
# #             current_subsection = text
# #             continue

# #         if current_category:
# #             buffer.append(text)
# #     flush()

# #     Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
# #     with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
# #         json.dump(structured, f, indent=2)

# #     categories_found = sorted(set(s["category"] for s in structured))
# #     print(f"Categories found ({len(categories_found)}): {categories_found}")
# #     print(f"Total sections extracted: {len(structured)}")

# #     subsection_counts = Counter(s["subsection"] for s in structured)
# #     print("\nSubsection distribution:")
# #     for subsection, count in subsection_counts.most_common():
# #         print(f"  {subsection}: {count}")


# # if __name__ == "__main__":
# #     main()

# from bs4 import BeautifulSoup
# import re, json
# from pathlib import Path
# from collections import Counter

# HTML_PATH = "data/owasp/agentic_top10.html"
# OUTPUT_JSON = "data/owasp/agentic_top10_structured.json"

# # Exact known headings, confirmed directly from your own diagnostic output —
# # no style matching needed, no guessing, just exact string membership.
# KNOWN_CATEGORIES = {
#     "ASI01: Agent Goal Hijack",
#     "ASI02: Tool Misuse and Exploitation",
#     "ASI03: Identity and Privilege Abuse",
#     "ASI04: Agentic Supply Chain Vulnerabilities",
#     "ASI05: Unexpected Code Execution (RCE)",
#     "ASI06: Memory & Context Poisoning",
#     "ASI07: Insecure Inter-Agent Communication",
#     "ASI08: Cascading Failures",
#     "ASI09: Human-Agent Trust Exploitation",
#     "ASI10: Rogue Agents",
# }

# SUBSECTION_NAMES = {
#     "Description",
#     "Common Examples of the Vulnerability",
#     "Example Attack Scenarios",
#     "Prevention and Mitigation Guidelines",
#     "References",
# }


# def main():
#     with open(HTML_PATH, encoding="utf-8") as f:
#         soup = BeautifulSoup(f, "html.parser")
#     spans = soup.find_all("span")

#     structured = []
#     current_category, current_subsection, buffer = None, "Description", []
#     category_hits = []

#     def flush():
#         if current_category and buffer:
#             structured.append({
#                 "category": current_category,
#                 "subsection": current_subsection,
#                 "text": " ".join(buffer).strip(),
#             })

#     for span in spans:
#         text = span.get_text().strip()
#         if not text or "(cid:" in text:
#             continue

#         if text in KNOWN_CATEGORIES:
#             category_hits.append(text)
#             flush(); buffer = []
#             current_category, current_subsection = text, "Description"
#             continue

#         if text in SUBSECTION_NAMES:
#             flush(); buffer = []
#             current_subsection = text
#             continue

#         if current_category:
#             buffer.append(text)
#     flush()

#     print(f"Category headings matched during loop: {len(category_hits)}")
#     print(f"Full list: {category_hits}\n")

#     Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
#     with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
#         json.dump(structured, f, indent=2)

#     categories_found = sorted(set(s["category"] for s in structured))
#     print(f"Categories found ({len(categories_found)}): {categories_found}")
#     print(f"Total sections extracted: {len(structured)}")

#     subsection_counts = Counter(s["subsection"] for s in structured)
#     print("\nSubsection distribution:")
#     for subsection, count in subsection_counts.most_common():
#         print(f"  {subsection}: {count}")


# if __name__ == "__main__":
#     main()
from bs4 import BeautifulSoup
import re, json
from pathlib import Path
from collections import Counter

HTML_PATH = "data/owasp/agentic_top10.html"
OUTPUT_JSON = "data/owasp/agentic_top10_structured.json"

KNOWN_CATEGORIES = [
    "ASI01: Agent Goal Hijack",
    "ASI02: Tool Misuse and Exploitation",
    "ASI03: Identity and Privilege Abuse",
    "ASI04: Agentic Supply Chain Vulnerabilities",
    "ASI05: Unexpected Code Execution (RCE)",
    "ASI06: Memory & Context Poisoning",
    "ASI07: Insecure Inter-Agent Communication",
    "ASI08: Cascading Failures",
    "ASI09: Human-Agent Trust Exploitation",
    "ASI10: Rogue Agents",
]

SUBSECTION_NAMES = {
    "Description",
    "Common Examples of the Vulnerability",
    "Example Attack Scenarios",
    "Prevention and Mitigation Guidelines",
    "References",
}


def normalize(text):
    """Collapses any run of whitespace (including line-wrap newlines
    inside a heading) down to a single space, so 'Tool Misuse and\nExploitation'
    matches 'Tool Misuse and Exploitation' regardless of where the PDF wrapped it."""
    return re.sub(r"\s+", " ", text).strip()


NORMALIZED_CATEGORY_MAP = {normalize(c): c for c in KNOWN_CATEGORIES}
NORMALIZED_SUBSECTIONS = {normalize(s): s for s in SUBSECTION_NAMES}


def main():
    with open(HTML_PATH, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    spans = soup.find_all("span")

    structured = []
    current_category, current_subsection, buffer = None, "Description", []
    category_hits = []

    def flush():
        if current_category and buffer:
            structured.append({
                "category": current_category,
                "subsection": current_subsection,
                "text": " ".join(buffer).strip(),
            })

    for span in spans:
        raw_text = span.get_text().strip()
        if not raw_text or "(cid:" in raw_text:
            continue

        norm = normalize(raw_text)

        if norm in NORMALIZED_CATEGORY_MAP:
            canonical = NORMALIZED_CATEGORY_MAP[norm]
            category_hits.append(canonical)
            flush(); buffer = []
            current_category, current_subsection = canonical, "Description"
            continue

        if norm in NORMALIZED_SUBSECTIONS:
            flush(); buffer = []
            current_subsection = NORMALIZED_SUBSECTIONS[norm]
            continue

        if current_category:
            buffer.append(raw_text)
    flush()

    print(f"Category headings matched during loop: {len(category_hits)}")
    print(f"Full list: {category_hits}\n")

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2)

    categories_found = sorted(set(s["category"] for s in structured))
    print(f"Categories found ({len(categories_found)}): {categories_found}")
    print(f"Total sections extracted: {len(structured)}")

    subsection_counts = Counter(s["subsection"] for s in structured)
    print("\nSubsection distribution:")
    for subsection, count in subsection_counts.most_common():
        print(f"  {subsection}: {count}")


if __name__ == "__main__":
    main()