import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import chromadb

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection = chroma_client.get_collection(name="owasp_risks")

NARRATIVE_SUBSECTIONS = ["Example Attack Scenarios", "Common Examples of the Vulnerability"]

MAX_DISTANCE = 0.95          # only genuinely close matches count
DRY_RUN = False


def get_company_linked_incident_ids():
    linked = (
        supabase.table("company_incidents")
        .select("incident_id, ai_incidents!inner(is_security_relevant)")
        .execute()
    )
    return {
        row["incident_id"]
        for row in linked.data
        if row.get("ai_incidents", {}).get("is_security_relevant")
    }


def classify(description):
    result = collection.query(
        query_texts=[description],
        n_results=1,   # just the single closest chunk — no vote needed at this strictness
        where={"subsection": {"$in": NARRATIVE_SUBSECTIONS}},
    )
    matches = result["metadatas"][0]
    distances = result["distances"][0]

    if not matches or distances[0] > MAX_DISTANCE:
        return "unclassified", distances[0] if distances else None

    return matches[0]["category"], distances[0]


def main():
    lead_incident_ids = get_company_linked_incident_ids()

    incidents = (
        supabase.table("ai_incidents")
        .select("id, aiid_incident_id, title, description")
        .eq("is_security_relevant", True)
        .execute()
    )
    to_process = [
        i for i in incidents.data
        if i["aiid_incident_id"] in lead_incident_ids or i["id"] in lead_incident_ids
    ]

    print(f"Processing {len(to_process)} company-linked incidents "
          f"(MAX_DISTANCE={MAX_DISTANCE}, DRY_RUN={DRY_RUN})\n")

    from collections import Counter
    tally = Counter()

    for incident in to_process:
        desc = incident.get("description")
        if not desc:
            continue

        category, distance = classify(desc)

        if not DRY_RUN:
            supabase.table("ai_incidents").update({
                "owasp_category": category
            }).eq("id", incident["id"]).execute()

        tally[category] += 1
        if category != "unclassified":
            print(f"  [{distance:.2f}] {incident['title'][:52]:<52} → {category}")

    print(f"\n--- Distribution ---")
    for category, count in tally.most_common():
        print(f"  {category}: {count}")

    total = sum(tally.values())
    classified = total - tally.get("unclassified", 0)
    if total:
        print(f"\n{classified}/{total} classified as high-confidence leads ({classified/total*100:.0f}%)")

    if DRY_RUN:
        print("\n(DRY_RUN — nothing written)")


if __name__ == "__main__":
    main()