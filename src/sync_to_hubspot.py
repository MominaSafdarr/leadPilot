import os
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

HUBSPOT_TOKEN = os.environ["HUBSPOT_ACCESS_TOKEN"]
HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type": "application/json",
}

TEST_BATCH_SIZE = 10


def ensure_property_exists(name, label, field_type="string", type_="string"):
    """Check if a custom property exists on the Companies object;
    create it if not. Makes the script self-sufficient — no manual
    dashboard clicking required, works the same on any fresh account."""
    check = requests.get(
        f"https://api.hubapi.com/crm/v3/properties/companies/{name}",
        headers=HEADERS,
    )
    if check.status_code == 200:
        return   # already exists, nothing to do

    print(f"  Property '{name}' doesn't exist yet — creating it")
    create = requests.post(
        "https://api.hubapi.com/crm/v3/properties/companies",
        headers=HEADERS,
        json={
            "name": name,
            "label": label,
            "type": type_,
            "fieldType": field_type,
            "groupName": "companyinformation",
        },
    )
    create.raise_for_status()


def find_existing_hubspot_company(domain):
    if not domain:
        return None
    resp = requests.post(
        "https://api.hubapi.com/crm/v3/objects/companies/search",
        headers=HEADERS,
        json={
            "filterGroups": [{
                "filters": [{"propertyName": "domain", "operator": "EQ", "value": domain}]
            }]
        },
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0]["id"] if results else None


def push_company(company):
    properties = {"name": company["name"]}
    if company.get("domain"):
        properties["domain"] = company["domain"]
    if company.get("industry"):
        properties["ai_industry_raw"] = company["industry"]   # custom field, no restricted list
    if company.get("description"):
        properties["description"] = company["description"]

    existing_id = find_existing_hubspot_company(company.get("domain"))

    if existing_id:
        resp = requests.patch(
            f"https://api.hubapi.com/crm/v3/objects/companies/{existing_id}",
            headers=HEADERS,
            json={"properties": properties},
        )
        action = "updated"
    else:
        resp = requests.post(
            "https://api.hubapi.com/crm/v3/objects/companies",
            headers=HEADERS,
            json={"properties": properties},
        )
        action = "created"

    if resp.status_code >= 400:
        raise Exception(f"{resp.status_code} — {resp.text}")

    hubspot_id = resp.json()["id"]
    return hubspot_id, action


def main():
    print("Checking custom properties exist...")
    ensure_property_exists("ai_industry_raw", "AI Industry (raw)", field_type="text", type_="string")

    companies = (
        supabase.table("companies")
        .select("id, name, domain, industry, description")
        .not_.is_("domain", "null")
        .limit(TEST_BATCH_SIZE)
        .execute()
    )
    print(f"\nFound {len(companies.data)} enriched companies ready to sync")

    for company in companies.data:
        print(f"\nSyncing: {company['name']}")
        try:
            hubspot_id, action = push_company(company)
            print(f"  {action} → HubSpot ID {hubspot_id}")

            supabase.table("crm_sync_log").insert({
                "company_id": company["id"],
                "hubspot_object_id": hubspot_id,
                "sync_status": "success",
            }).execute()

        except Exception as e:
            print(f"  Failed: {e}")
            supabase.table("crm_sync_log").insert({
                "company_id": company["id"],
                "sync_status": "failed",
                "error_message": str(e),
            }).execute()

        time.sleep(1)

    print("\nDone.")


if __name__ == "__main__":
    main()