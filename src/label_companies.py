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
SLEEP_SECONDS = 3

RUBRIC = """
Score leads for AptaSentry, which sells AI/LLM security products
(red-teaming, runtime guardrails, AI supply-chain validation) to security
and ML platform teams.

good_fit: has an AI incident, is hiring for AI safety/security roles,
is in a regulated industry (finance, healthcare, government, insurance),
or has deployed customer-facing AI features.

not_fit: none of the above apply.
"""


def get_context(company):
    parts = [f"Company: {company['name']}"]
    if company.get("industry"):
        parts.append(f"Industry: {company['industry']}")
    if company.get("description"):
        parts.append(f"Description: {company['description']}")

    incidents = supabase.table("company_incidents").select("relationship").eq("company_id", company["id"]).execute()
    parts.append(f"Incident count: {len(incidents.data)}")

    jobs = supabase.table("job_postings").select("title").eq("company_id", company["id"]).execute()
    parts.append(f"Job posting count: {len(jobs.data)}")

    return "\n".join(parts)


def get_label(context):
    prompt = f"""{RUBRIC}

Return ONLY valid JSON, no markdown fences: {{"label": "good_fit" or "not_fit"}}

COMPANY INFO:
{context}
"""
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0},
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    cleaned = raw.strip().strip("`").lstrip("json").strip()
    return json.loads(cleaned)["label"]


def main():
    companies = supabase.table("companies").select("id, name, industry, description").not_.is_("domain", "null").is_("ai_label", "null").execute()
    print(f"Labeling {len(companies.data)} companies")

    for c in companies.data:
        try:
            label = get_label(get_context(c))
            supabase.table("companies").update({"ai_label": label}).eq("id", c["id"]).execute()
            print(f"{c['name']}: {label}")
        except Exception as e:
            print(f"{c['name']}: failed — {e}")
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()