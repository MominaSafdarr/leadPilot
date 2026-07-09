import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GROQ_MODEL = "llama-3.1-8b-instant"
TEST_BATCH_SIZE = 100
SLEEP_SECONDS = 2
MAX_RETRIES = 3

# Still worth keeping as a fast first-pass filter — catches obvious cases
# without spending an API call at all
JUNK_NAME_PATTERNS = [
    "scammers", "actors", "anonymous", "unidentified", "unknown",
    "hackers", "users", "community", "impersonat", "criminals",
    "blackmail", "sextortion", "deepfake", "scam", "fraud",
    "perpetrator", "malicious", "creators", "operators",
]


def is_junk_name(name):
    name_lower = name.lower()
    return any(pattern in name_lower for pattern in JUNK_NAME_PATTERNS)


def delete_company(company_id):
    """Cascades to company_incidents automatically via the schema's
    ON DELETE CASCADE."""
    supabase.table("companies").delete().eq("id", company_id).execute()


def call_with_retry(fn, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if "432" in str(e) or "433" in str(e):
                raise Exception("Tavily quota exhausted — skipping, no point retrying")
            wait = 2 ** attempt * 5
            print(f"    Retry {attempt + 1}/{MAX_RETRIES} after {wait}s — {e}")
            time.sleep(wait)
        except requests.exceptions.ConnectionError as e:
            wait = 2 ** attempt * 5
            print(f"    Retry {attempt + 1}/{MAX_RETRIES} after {wait}s — {e}")
            time.sleep(wait)
    raise Exception(f"Failed after {MAX_RETRIES} retries")

def tavily_search(company_name):
    def _call():
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": f"{company_name} company",
                "max_results": 3,
                "include_answer": True,
            },
        )
        resp.raise_for_status()
        return resp.json()
    return call_with_retry(_call)


def build_context(tavily_data):
    context = tavily_data.get("answer", "") + "\n\n"
    for r in tavily_data.get("results", [])[:3]:
        context += f"{r.get('title')}: {r.get('content')}\n\n"
    return context


def groq_extract(company_name, context):
    def _call():
        prompt = f"""You are extracting facts about a SPECIFIC, REAL COMPANY named "{company_name}".

Some inputs are NOT real companies — they may be descriptions of anonymous
groups, categories of malicious actors, or generic activities (e.g.
"Scammers", "Deepfake Creators", "Cybercriminals"). If "{company_name}"
is not a specific, identifiable, real company, return every field as null.
Do NOT substitute or borrow information from unrelated real companies that
happen to appear in the source text below — only use information that is
clearly and specifically about "{company_name}" itself.

Return ONLY valid JSON, no markdown formatting, no explanation:

{{
  "domain": string or null,
  "industry": string or null,
  "employee_count_min": integer or null,
  "employee_count_max": integer or null,
  "description": string or null,
  "funding_notes": string or null
}}

TEXT:
{context}
"""
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
        )
        resp.raise_for_status()
        raw_output = resp.json()["choices"][0]["message"]["content"]
        cleaned = raw_output.strip().strip("`").lstrip("json").strip()
        return json.loads(cleaned)
    return call_with_retry(_call)


def main():
    companies = (
        supabase.table("companies")
        .select("id, name")
        .is_("domain", "null")
        .order("created_at")   # <-- deterministic: always processes oldest-unenriched-first
        .limit(TEST_BATCH_SIZE)
        .execute()
    )
    print(f"Found {len(companies.data)} companies needing enrichment")

    deleted_junk = 0
    deleted_empty = 0
    enriched = 0
    failed = 0
    consecutive_rate_limits = 0

    for company in companies.data:
        name = company["name"]

        if is_junk_name(name):
            print(f"\nDeleting (matched junk pattern): {name}")
            delete_company(company["id"])
            deleted_junk += 1
            continue

        print(f"\nEnriching: {name}")
        try:
            tavily_data = tavily_search(name)
            context = build_context(tavily_data)
            extracted = groq_extract(name, context)
            consecutive_rate_limits = 0   # reset on any success

        except requests.exceptions.HTTPError as e:
            if "429" in str(e):
                consecutive_rate_limits += 1
                print(f"  Rate limited ({consecutive_rate_limits} in a row)")
                if consecutive_rate_limits >= 3:
                    print("\nHit sustained rate limiting — stopping run early.")
                    print("Rerun the script later; ORDER BY created_at means")
                    print("it will pick up where this left off, not repeat these.")
                    break
            else:
                print(f"  Skipped — error: {e}")
            failed += 1
            time.sleep(SLEEP_SECONDS)
            continue

        except Exception as e:
            print(f"  Skipped — error: {e}")
            failed += 1
            time.sleep(SLEEP_SECONDS)
            continue

        if not extracted.get("domain") and not extracted.get("industry"):
            print(f"  Deleting (no real company found): {name}")
            delete_company(company["id"])
            deleted_empty += 1
            time.sleep(SLEEP_SECONDS)
            continue

        update_fields = {k: v for k, v in extracted.items() if v is not None}
        supabase.table("companies").update(update_fields).eq("id", company["id"]).execute()

        supabase.table("company_enrichment").insert({
            "company_id": company["id"],
            "source": "tavily_groq",
            "raw_response": {"tavily": tavily_data, "extracted": extracted},
        }).execute()

        print(f"  Extracted: {extracted}")
        enriched += 1
        time.sleep(SLEEP_SECONDS)

    print(f"\nDone. Enriched: {enriched}, Deleted (junk pattern): {deleted_junk}, "
          f"Deleted (empty result): {deleted_empty}, Failed: {failed}")
    
if __name__ == "__main__":
    main()