import os
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)


def slug_to_readable_name(slug):
    """AIID slugs are lowercase-hyphenated, e.g. 'youtube' or
    'google-llc' — turn into something presentable as a company name."""
    return slug.replace("-", " ").title()


def find_or_create_company(slug):
    readable_name = slug_to_readable_name(slug)

    existing = (
        supabase.table("companies")
        .select("id")
        .ilike("name", readable_name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"], 0.9   # matched by name, decent confidence

    created = supabase.table("companies").insert({"name": readable_name}).execute()
    return created.data[0]["id"], 1.0   # newly created from this slug, high confidence


def link_incident(incident, slugs, relationship):
    for slug in slugs:
        company_id, confidence = find_or_create_company(slug)
        try:
            supabase.table("company_incidents").insert({
                "company_id": company_id,
                "incident_id": incident["id"],
                "relationship": relationship,
                "match_confidence": confidence,
            }).execute()
        except Exception:
            pass   # already linked — primary key conflict, safe to skip


def main():
    incidents = supabase.table("ai_incidents").select("id, deployers, developers").execute()
    print(f"Processing {len(incidents.data)} incidents")

    for incident in incidents.data:
        if incident.get("deployers"):
            link_incident(incident, incident["deployers"], "deployer")
        if incident.get("developers"):
            link_incident(incident, incident["developers"], "developer")

    print("Done.")


if __name__ == "__main__":
    main()