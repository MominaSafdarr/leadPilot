import os
import sys
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

CATEGORY_TO_PRODUCT = {
    "LLM01:2025 Prompt Injection": "adversarial red-teaming",
    "LLM02:2025 Sensitive Information Disclosure": "runtime guardrails",
    "LLM03:2025 Supply Chain": "AI supply-chain validation",
    "LLM04: Data and Model Poisoning": "AI supply-chain validation",
    "LLM05:2025 Improper Output Handling": "runtime guardrails",
    "LLM06:2025 Excessive Agency": "agentic AI security",
    "LLM07:2025 System Prompt Leakage": "runtime guardrails",
    "LLM08:2025 Vector and Embedding Weaknesses": "AI supply-chain validation",
    "LLM09:2025 Misinformation": "runtime guardrails",
    "LLM10:2025 Unbounded Consumption": "runtime guardrails",
    "ASI01: Agent Goal Hijack": "agentic AI security",
    "ASI02: Tool Misuse and Exploitation": "agentic AI security",
    "ASI03: Identity and Privilege Abuse": "agentic AI security",
    "ASI04: Agentic Supply Chain Vulnerabilities": "AI supply-chain validation",
    "ASI05: Unexpected Code Execution (RCE)": "adversarial red-teaming",
    "ASI06: Memory & Context Poisoning": "agentic AI security",
    "ASI07: Insecure Inter-Agent Communication": "agentic AI security",
    "ASI08: Cascading Failures": "agentic AI security",
    "ASI09: Human-Agent Trust Exploitation": "runtime guardrails",
    "ASI10: Rogue Agents": "agentic AI security",
}
DEFAULT_PRODUCT = "AI security assessment"


def get_company(company_id):
    return supabase.table("companies").select("*").eq("id", company_id).single().execute().data


def get_classified_incident(company_id):
    """Returns the company's first incident that has a real OWASP category
    (not null, not 'unclassified'), or None if it has no classified incident."""
    links = (
        supabase.table("company_incidents")
        .select("ai_incidents(title, description, owasp_category)")
        .eq("company_id", company_id)
        .execute()
    )
    for link in links.data:
        inc = link.get("ai_incidents")
        if inc and inc.get("owasp_category") and inc["owasp_category"] != "unclassified":
            return inc
    return None


def get_job_titles(company_id):
    jobs = (
        supabase.table("job_postings")
        .select("title")
        .eq("company_id", company_id)
        .execute()
    )
    return [j["title"] for j in jobs.data if j.get("title")]


def count_similar_incidents(owasp_category, exclude_incident_title):
    result = (
        supabase.table("ai_incidents")
        .select("id", count="exact")
        .eq("owasp_category", owasp_category)
        .execute()
    )
    return max(result.count - 1, 0)  # minus this company's own


def call_groq(prompt):
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def build_incident_prompt(company, incident, product, similar_count):
    return f"""Write a short, professional cold outreach email from AptaSentry
(an AI security company) to {company['name']}.

Use ONLY the facts below. Do not invent customers, results, statistics, or
any claim not stated here.

COMPANY:
Industry: {company.get('industry', 'unknown')}
Description: {company.get('description', 'unknown')}

DOCUMENTED INCIDENT (real, on record):
{incident['description']}

This incident reflects a risk category known as "{incident['owasp_category']}".
There are approximately {similar_count} other documented incidents of this same
category across the industry.

RELEVANT APTASENTRY OFFERING (mention this specifically, invent no others):
{product}

Keep it under 130 words. Reference their specific incident and the risk category."""


def build_hiring_prompt(company, job_titles, product):
    titles_str = ", ".join(job_titles[:3])
    return f"""Write a short, professional cold outreach email from AptaSentry
(an AI security company) to {company['name']}.

Use ONLY the facts below. Do not invent incidents, customers, results, or
statistics. This company has NO documented security incident — do not imply
or fabricate one.

COMPANY:
Industry: {company.get('industry', 'unknown')}
Description: {company.get('description', 'unknown')}

SIGNAL — they are actively hiring for these roles:
{titles_str}

This hiring activity suggests they are investing in AI/security capability.

RELEVANT APTASENTRY OFFERING (mention this specifically, invent no others):
{product}

Keep it under 130 words. Reference their hiring signal, not any incident."""


def generate_outreach(company_id):
    company = get_company(company_id)
    incident = get_classified_incident(company_id)

    if incident:
        # A-tier: incident-based
        product = CATEGORY_TO_PRODUCT.get(incident["owasp_category"], DEFAULT_PRODUCT)
        similar = count_similar_incidents(incident["owasp_category"], incident["title"])
        prompt = build_incident_prompt(company, incident, product, similar)
        path, matched = "incident", incident["owasp_category"]
    else:
        # B-tier: hiring-signal
        job_titles = get_job_titles(company_id)
        if not job_titles:
            print(f"  {company['name']}: no incident and no job postings — skipping")
            return None
        product = DEFAULT_PRODUCT  # hiring path isn't tied to a specific risk category
        prompt = build_hiring_prompt(company, job_titles, product)
        path, matched = "hiring", None

    email_text = call_groq(prompt)

    supabase.table("outreach_messages").insert({
        "company_id": company_id,
        "generated_text": email_text,
        "matched_product": matched or path,
    }).execute()

    return {"path": path, "text": email_text, "product": product}


if __name__ == "__main__":
    company_id = sys.argv[1] if len(sys.argv) > 1 else input("Enter a company_id: ")
    result = generate_outreach(company_id)
    if result:
        print(f"\n--- Path: {result['path']} | Product: {result['product']} ---\n")
        print(result["text"])
        print("\nSaved to outreach_messages.")