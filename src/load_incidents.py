import os
import json
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

CSV_PATH = "data/mongodump_full_snapshot/incidents.csv"
CUTOFF_DATE = "2024-01-01"
RUN_FULL = True        # flip to True once the 20-row test looks right
TEST_BATCH_SIZE = 20


def safe_json_parse(value):
    """AIID stores list columns as JSON strings, e.g. '["youtube"]'.
    A few rows may be missing or malformed — fail that one row to None
    instead of crashing the whole load."""
    if pd.isna(value):
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} total incidents from CSV")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    recent = df[df["date"] >= CUTOFF_DATE].copy()
    recent = recent.sort_values("date", ascending=False)
    print(f"{len(recent)} incidents on or after {CUTOFF_DATE}")

    batch = recent if RUN_FULL else recent.head(TEST_BATCH_SIZE)
    print(f"Preparing {len(batch)} rows for insert (RUN_FULL={RUN_FULL})")

    rows = []
    for _, row in batch.iterrows():
        rows.append({
            "aiid_incident_id": int(row["incident_id"]),
            "title": row["title"],
            "description": row["description"],
            "incident_date": row["date"].strftime("%Y-%m-%d"),
            "deployers": safe_json_parse(row["Alleged deployer of AI system"]),
            "developers": safe_json_parse(row["Alleged developer of AI system"]),
            "harmed_parties": safe_json_parse(row["Alleged harmed or nearly harmed parties"]),
            "report_ids": safe_json_parse(row["reports"]),
        })

    result = supabase.table("ai_incidents").upsert(
        rows, on_conflict="aiid_incident_id"
    ).execute()

    print(f"\nInserted/updated {len(result.data)} rows. Sample:")
    for r in result.data[:5]:
        print(f"  #{r['aiid_incident_id']} ({r['incident_date']}): {r['title']}")


if __name__ == "__main__":
    main()