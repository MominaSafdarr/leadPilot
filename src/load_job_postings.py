import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

ADZUNA_APP_ID = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY = os.environ["ADZUNA_APP_KEY"]

# Search terms matching the AptaSentry ICP's hiring-intent signal
SEARCH_TERMS = [
    "AI safety",
    "responsible AI",
    "AI red team",
    "ML security",
    "trust and safety engineer",
    "AI governance",
    "LLM security",
    "AI compliance",
]

RESULTS_PER_PAGE =20  # keep small for the first test run, raise once confirmed


def get_or_create_company(name):
    """Match by lowercased name; create a bare row if this company
    hasn't been seen by any source yet."""
    name_clean = name.strip()
    existing = (
        supabase.table("companies")
        .select("id")
        .ilike("name", name_clean)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    created = supabase.table("companies").insert({"name": name_clean}).execute()
    return created.data[0]["id"]


def fetch_jobs(query):
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "results_per_page": RESULTS_PER_PAGE,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get("results", [])


def main():
    total_inserted = 0

    for term in SEARCH_TERMS:
        print(f"\nSearching Adzuna for: '{term}'")
        jobs = fetch_jobs(term)
        print(f"  {len(jobs)} results")

        rows = []
        for job in jobs:
            company_name = job.get("company", {}).get("display_name")
            if not company_name:
                continue   # skip postings with no company name — nothing to link to

            company_id = get_or_create_company(company_name)

            rows.append({
                "company_id": company_id,
                "adzuna_job_id": str(job["id"]),
                "title": job.get("title"),
                "description": job.get("description"),
                "company_name_raw": company_name,
                "location_display": job.get("location", {}).get("display_name"),
                "category": job.get("category", {}).get("label") if isinstance(job.get("category"), dict) else job.get("category"),
                "contract_time": job.get("contract_time"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_is_predicted": bool(int(job.get("salary_is_predicted", 0))) if job.get("salary_is_predicted") is not None else None,
                "redirect_url": job.get("redirect_url"),
                "posted_date": job.get("created"),
            })

        if rows:
            result = supabase.table("job_postings").upsert(
                rows, on_conflict="adzuna_job_id"
            ).execute()
            total_inserted += len(result.data)
            print(f"  Inserted/updated {len(result.data)} job postings")

        time.sleep(1)   # be polite to the free tier between search terms

    print(f"\nDone. {total_inserted} total job postings processed.")


if __name__ == "__main__":
    main()