import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

REGULATED_KEYWORDS = ["financ", "health", "insur", "govern", "bank", "defense"]

FEATURE_LABELS = {
    "incident_count": "incident history",
    "job_posting_count": "hiring activity",
    "is_regulated": "regulated industry",
}


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


def name_cluster(centroid_scaled, feature_names):
    """Names a cluster by whichever feature deviates most from the overall
    mean (in standardized units), not by an arbitrary raw threshold.
    If nothing deviates meaningfully, says so instead of forcing a story."""
    deviations = dict(zip(feature_names, centroid_scaled))
    dominant_feature = max(deviations, key=lambda k: abs(deviations[k]))
    dominant_value = deviations[dominant_feature]

    if abs(dominant_value) < 0.4:
        return "No strong distinguishing signal"

    direction = "High" if dominant_value > 0 else "Low"
    return f"{direction} {FEATURE_LABELS[dominant_feature]}"


def main():
    companies = supabase.table("companies").select("id, name, industry").not_.is_("domain", "null").execute()
    rows = [build_features(c) for c in companies.data]
    df = pd.DataFrame(rows)

    features = list(FEATURE_LABELS.keys())
    X = df[features]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Pick k automatically via silhouette score
    best_k, best_score = 2, -1
    for k in range(2, min(5, len(df))):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        print(f"k={k}: silhouette score {score:.3f}")
        if score > best_score:
            best_k, best_score = k, score

    print(f"\nUsing k={best_k} (silhouette score {best_score:.3f})")
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X_scaled)

    cluster_names = {}
    for cluster_id in range(best_k):
        cluster_rows = df[df["cluster"] == cluster_id]
        raw_avg = cluster_rows[features].mean().values
        centroid_scaled = kmeans.cluster_centers_[cluster_id]

        cluster_names[cluster_id] = name_cluster(centroid_scaled, features)

        print(f"\nCluster {cluster_id} — '{cluster_names[cluster_id]}' ({len(cluster_rows)} companies)")
        print(f"  Raw averages — incidents: {raw_avg[0]:.1f}, job postings: {raw_avg[1]:.1f}, regulated: {raw_avg[2]:.0%}")
        print(f"  Standardized deviations from overall mean: {dict(zip(features, centroid_scaled.round(2)))}")

    for _, row in df.iterrows():
        supabase.table("companies").update({
            "segment_cluster": int(row["cluster"]),
            "segment_label": cluster_names[row["cluster"]],
        }).eq("id", row["company_id"]).execute()

    print("\nDone.")


if __name__ == "__main__":
    main()