import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut, cross_val_score

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

REGULATED_KEYWORDS = ["financ", "health", "insur", "govern", "bank", "defense"]


def build_features(company):
    incidents = supabase.table("company_incidents").select("relationship").eq("company_id", company["id"]).execute()
    jobs = supabase.table("job_postings").select("title").eq("company_id", company["id"]).execute()
    industry = (company.get("industry") or "").lower()

    return {
        "company_id": company["id"],
        "name": company["name"],
        "incident_count": len(incidents.data),
        "job_posting_count": len(jobs.data),
        "is_regulated": int(any(k in industry for k in REGULATED_KEYWORDS)),
    }


def main():
    companies = (
        supabase.table("companies")
        .select("id, name, industry, ai_label")
        .not_.is_("domain", "null")
        .execute()
    )
    rows = [build_features(c) | {"ai_label": c["ai_label"]} for c in companies.data]
    df = pd.DataFrame(rows)

    labeled = df[df["ai_label"].notna()].copy()
    labeled["target"] = (labeled["ai_label"] == "good_fit").astype(int)

    features = ["incident_count", "job_posting_count", "is_regulated"]
    X_train = labeled[features]
    y_train = labeled["target"]

    print(f"Training on {len(labeled)} labeled companies")
    print(f"Class balance: {y_train.value_counts().to_dict()}")

    model = LogisticRegression()
    scores = cross_val_score(model, X_train, y_train, cv=LeaveOneOut())
    print(f"Leave-one-out CV accuracy: {scores.mean():.2%}")

    model.fit(X_train, y_train)
    print(f"\nCoefficients: {dict(zip(features, model.coef_[0]))}")

    X_all = df[features]
    probabilities = model.predict_proba(X_all)[:, 1]

    for i, row in df.iterrows():
        score = round(probabilities[i] * 100)
        tier = "hot" if score >= 70 else "warm" if score >= 40 else "cold"
        supabase.table("companies").update({
            "lead_score": score,
            "lead_tier": tier
        }).eq("id", row["company_id"]).execute()
        print(f"{row['name']}: {score} ({tier})")

    print("\nDone.")


if __name__ == "__main__":
    main()