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

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_MODEL = "llama-3.1-8b-instant"   # classification is simple, doesn't need 70B
BATCH_SIZE = 1000
SLEEP_SECONDS = 1.5
MAX_RETRIES = 3

# Only these two types are kept as potential leads
VALID_TYPES = {"company", "government_agency"}


def call_with_retry(fn, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            wait = 2 ** attempt * 5
            print(f"    Retry {attempt + 1}/{MAX_RETRIES} after {wait}s — {e}")
            time.sleep(wait)
    raise Exception(f"Failed after {MAX_RETRIES} retries")


def classify_entity(name):
    def _call():
        prompt = f"""Classify the following name into exactly one category.
This is NOT about researching the entity — just judge from the name and
your general knowledge what KIND of thing it refers to.

Name: "{name}"

Categories:
- company: a real for-profit or nonprofit business/organization
- government_agency: a government body, ministry, or public agency
- individual_person: a named human being, not an organization
- educational_institution: a school, college, university, or exam board
- court_judiciary: a court or judicial body
- media_outlet: a newspaper, TV station, or social media page/account
- anonymous_group: a description of unidentified people or a vague
  category of actors (e.g. "scammers", "cybercriminals", "deepfake creators")
- other: anything that doesn't fit the above

Return ONLY valid JSON, no markdown: {{"entity_type": "one_of_the_above"}}
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
        raw = resp.json()["choices"][0]["message"]["content"]
        cleaned = raw.strip().strip("`").lstrip("json").strip()
        return json.loads(cleaned)["entity_type"]
    return call_with_retry(_call)


def main():
    companies = (
        supabase.table("companies")
        .select("id, name")
        .is_("entity_type", "null")   # only unclassified ones — safe to rerun
        .limit(BATCH_SIZE)
        .execute()
    )
    print(f"Classifying {len(companies.data)} companies")

    kept = 0
    deleted = 0
    failed = 0

    for c in companies.data:
        try:
            entity_type = classify_entity(c["name"])
        except Exception as e:
            print(f"{c['name']}: classification failed — {e}")
            failed += 1
            continue

        if entity_type in VALID_TYPES:
            supabase.table("companies").update({"entity_type": entity_type}).eq("id", c["id"]).execute()
            print(f"{c['name']}: KEPT ({entity_type})")
            kept += 1
        else:
            supabase.table("companies").delete().eq("id", c["id"]).execute()
            print(f"{c['name']}: DELETED ({entity_type})")
            deleted += 1

        time.sleep(SLEEP_SECONDS)

    print(f"\nDone. Kept: {kept}, Deleted: {deleted}, Failed: {failed}")


if __name__ == "__main__":
    main()