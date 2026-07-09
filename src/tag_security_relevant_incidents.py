import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

CSV_PATH = "data/mongodump_full_snapshot/classifications_MIT.csv"

# Confirm these exact strings against the real unique values printed below
# before trusting this filter
SECURITY_RELEVANT_DOMAINS = [
    "Privacy",     # matches "2. Privacy & Security"
    "Malicious",   # matches "4. Malicious Actors & Misuse"
]


def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} MIT classification rows")

    print("\nAll unique Risk Domain values found:")
    for domain in df["Risk Domain"].dropna().unique():
        print(f"  {domain}")

    df["is_security_relevant"] = df["Risk Domain"].apply(
        lambda d: isinstance(d, str) and any(k in d for k in SECURITY_RELEVANT_DOMAINS)
    )

    relevant_count = df["is_security_relevant"].sum()
    print(f"\n{relevant_count} of {len(df)} rows flagged as security-relevant")

    updated = 0
    for _, row in df.iterrows():
        result = (
            supabase.table("ai_incidents")
            .update({
                "mit_risk_domain": row["Risk Domain"],
                "is_security_relevant": bool(row["is_security_relevant"]),
            })
            .eq("aiid_incident_id", int(row["Incident ID"]))
            .execute()
        )
        if result.data:
            updated += 1

    print(f"\nDone. Updated {updated} incidents in Supabase.")


if __name__ == "__main__":
    main()