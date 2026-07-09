import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
import os
from dotenv import load_dotenv
from supabase import create_client

from generate_outreach import generate_outreach
from classify_incidents import main as classify_incidents_main
from load_job_postings import main as ingest_jobs_main
from classify_and_clean_companies import main as classify_entities_main
from enrich_companies import main as enrich_main
from tag_security_relevant_incidents import main as tag_security_main
from label_companies import main as label_companies_main
from train_scoring_model import main as train_scoring_main
from cluster_companies import main as cluster_main

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

app = FastAPI(title="LeadPilot API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/leads")
def get_leads():
    result = (
        supabase.table("companies")
        .select("id, name, lead_score, lead_tier, segment_label")
        .not_.is_("lead_score", "null")
        .order("lead_score", desc=True)
        .execute()
    )
    return {"count": len(result.data), "leads": result.data}


@app.post("/ingest-jobs")
def ingest_jobs():
    """Pulls fresh Adzuna postings, creates/matches companies."""
    ingest_jobs_main()
    return {"status": "ok", "step": "ingest-jobs"}


@app.post("/enrich")
def enrich():
    """Classifies non-company entities (deletes junk), then enriches
    remaining companies via Tavily + Groq."""
    classify_entities_main()
    enrich_main()
    return {"status": "ok", "step": "enrich"}


@app.post("/classify-incidents")
def classify_incidents_endpoint():
    """Tags security-relevant incidents (MIT taxonomy), then runs the
    RAG classification against the existing OWASP index — no re-embedding."""
    tag_security_main()
    classify_incidents_main()
    return {"status": "ok", "step": "classify-incidents"}


@app.post("/score-and-cluster")
def score_and_cluster():
    """Labels companies via Groq, trains the logistic regression scorer,
    then runs KMeans segmentation."""
    label_companies_main()
    train_scoring_main()
    cluster_main()
    return {"status": "ok", "step": "score-and-cluster"}


@app.post("/generate-outreach-batch")
def generate_outreach_batch():
    """Generates drafts for qualified leads that don't have one yet."""
    leads = (
        supabase.table("companies")
        .select("id")
        .not_.is_("lead_score", "null")
        .execute()
    )
    existing_drafts = supabase.table("outreach_messages").select("company_id").execute()
    already_drafted = {row["company_id"] for row in existing_drafts.data}

    generated = 0
    skipped = 0
    for lead in leads.data:
        if lead["id"] in already_drafted:
            continue
        result = generate_outreach(lead["id"])
        if result:
            generated += 1
        else:
            skipped += 1

    return {"status": "ok", "generated": generated, "skipped": skipped}


@app.post("/generate-outreach/{company_id}")
def outreach_endpoint(company_id: str):
    result = generate_outreach(company_id)
    if result is None:
        return {"status": "skipped", "reason": "no incident or job postings"}
    return {"status": "ok", "path": result["path"], "product": result["product"]}