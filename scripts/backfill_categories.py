#!/usr/bin/env python3
"""Seed categories table and backfill problems.category with matching slugs.

Run from the backend directory:
    cd src/backend && python ../../scripts/backfill_categories.py
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend"))

from sqlalchemy import text
from app.core.database import SessionLocal

# ── Category definitions ──────────────────────────────────────────────────────

CATEGORIES = [
    {"name": "Programming",  "slug": "programming",  "description": "Coding and software development"},
    {"name": "DevOps",       "slug": "devops",        "description": "Deployment, containers, and infrastructure"},
    {"name": "AI & ML",      "slug": "ai-ml",         "description": "Artificial intelligence and machine learning"},
    {"name": "Security",     "slug": "security",      "description": "Security and privacy"},
    {"name": "Networking",   "slug": "networking",    "description": "Networking and internet"},
    {"name": "Hardware",     "slug": "hardware",      "description": "Hardware and electronics"},
    {"name": "Career",       "slug": "career",        "description": "Jobs and career advice"},
    {"name": "Technology",   "slug": "technology",    "description": "General technology"},
    {"name": "Open Source",  "slug": "open-source",   "description": "Open source projects"},
    {"name": "Other",        "slug": "other",         "description": "Other topics"},
]

# ── Subreddit → slug mapping ──────────────────────────────────────────────────

SUBREDDIT_MAP: dict[str, str] = {
    # Programming
    "programming": "programming", "learnprogramming": "programming",
    "python": "programming", "javascript": "programming", "java": "programming",
    "cpp": "programming", "rust": "programming", "golang": "programming",
    "typescript": "programming", "webdev": "programming", "reactjs": "programming",
    "node": "programming", "django": "programming", "flask": "programming",
    "linux": "programming", "bash": "programming", "compsci": "programming",
    "learnpython": "programming", "ruby": "programming", "swift": "programming",
    "dartlang": "programming", "gamedev": "programming", "unity3d": "programming",
    "unrealengine": "programming", "csharp": "programming", "dotnet": "programming",
    "php": "programming", "scala": "programming", "haskell": "programming",
    "sql": "programming", "database": "programming", "databases": "programming",
    "PostgreSQL": "programming", "mysql": "programming", "mongodb": "programming",
    "git": "programming", "github": "programming",

    # DevOps
    "devops": "devops", "docker": "devops", "kubernetes": "devops",
    "terraform": "devops", "aws": "devops", "azure": "devops",
    "googlecloud": "devops", "sysadmin": "devops", "homelab": "devops",
    "selfhosted": "devops", "ansible": "devops", "jenkins": "devops",
    "cicd": "devops", "nginx": "devops", "apache": "devops",
    "linuxadmin": "devops", "debian": "devops", "ubuntu": "devops",

    # AI & ML
    "MachineLearning": "ai-ml", "deeplearning": "ai-ml", "artificial": "ai-ml",
    "ChatGPT": "ai-ml", "OpenAI": "ai-ml", "LocalLLaMA": "ai-ml",
    "LanguageModels": "ai-ml", "mlops": "ai-ml", "datascience": "ai-ml",
    "learnmachinelearning": "ai-ml", "StableDiffusion": "ai-ml",
    "singularity": "ai-ml", "neuralnetworks": "ai-ml", "computervision": "ai-ml",
    "NLP": "ai-ml", "llm": "ai-ml",
    "GeminiAI": "ai-ml", "GoogleGeminiAI": "ai-ml", "ClaudeAI": "ai-ml",
    "ClaudeCode": "ai-ml", "codex": "ai-ml", "MindAI": "ai-ml",
    "ZaiGLM": "ai-ml", "kimi": "ai-ml", "openclaw": "ai-ml",
    "openrouter": "ai-ml", "ArcRaiders": "ai-ml",

    # Security
    "netsec": "security", "cybersecurity": "security", "hacking": "security",
    "privacy": "security", "crypto": "security", "cryptography": "security",
    "reverseengineering": "security", "malware": "security",
    "AskNetsec": "security", "blackhat": "security", "redteamsec": "security",

    # Networking
    "networking": "networking", "pihole": "networking", "ccna": "networking",
    "wifi": "networking", "homenetworking": "networking", "openwrt": "networking",
    "pfBlockerNG": "networking", "pfsense": "networking",

    # Hardware
    "hardware": "hardware", "buildapc": "hardware", "raspberry_pi": "hardware",
    "arduino": "hardware", "embedded": "hardware", "electronics": "hardware",
    "3Dprinting": "hardware", "printers": "hardware", "esp8266": "hardware",
    "FPGA": "hardware",

    # Career
    "cscareerquestions": "career", "jobs": "career", "freelance": "career",
    "forhire": "career", "remotework": "career", "ITCareerQuestions": "career",
    "ExperiencedDevs": "career",

    # Technology
    "technology": "technology", "tech": "technology", "gadgets": "technology",
    "software": "technology", "opensource": "technology",
    "programming": "programming",  # overridden above – kept for clarity
}

# ── Keyword fallback (title + body, lowercase) ───────────────────────────────

KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["docker", "kubernetes", "k8s", "helm", "terraform", "ci/cd", "pipeline",
      "deployment", "nginx", "ansible", "jenkins", "gitlab ci", "github action",
      "aws", "azure", "gcp", "cloud run", "lambda"], "devops"),
    (["machine learning", "deep learning", "neural network", "large language model",
      "chatgpt", "openai api", "stable diffusion", "pytorch", "tensorflow",
      "huggingface", "fine-tuning", "fine tuning", "reinforcement learning",
      "artificial intelligence", "computer vision", "natural language processing",
      "generative ai", "vector database", "embedding model",
      "llama", "mistral", "gemini api", "claude api", "claude.ai",
      "anthropic api", "gpt-4", "gpt-3", "gpt4", "langchain",
      "semantic search", "rag pipeline", "retrieval augmented"], "ai-ml"),
    (["security", "vulnerability", "exploit", "hack", "phishing", "malware",
      "ransomware", "ssl", "tls", "firewall", "breach", "password",
      "authentication", "oauth", "jwt", "xss", "sql injection", "cve"], "security"),
    (["network", "wifi", "router", "dns", "vpn", "ip address", "tcp",
      "udp", "bandwidth", "latency", "proxy", "firewall", "subnet"], "networking"),
    (["cpu", "gpu", "ram", "motherboard", "ssd", "raspberry pi", "arduino",
      "electronics", "3d print", "soldering", "pcb", "microcontroller"], "hardware"),
    (["salary", "job offer", "career", "interview", "resume", "cv",
      "hiring", "freelance", "remote work", "recruiter", "promotion"], "career"),
    (["open source", "github", "contribution", "pull request", "fork",
      "license", "mit license", "apache license", "gpl"], "open-source"),
]


def _infer_category(subreddit: str | None, title: str, body: str | None) -> str:
    # 1. Try exact subreddit match
    if subreddit:
        slug = SUBREDDIT_MAP.get(subreddit) or SUBREDDIT_MAP.get(subreddit.lower())
        if slug:
            return slug

    # 2. Keyword search in title + body
    text_lower = (title or "").lower() + " " + (body or "").lower()
    for keywords, slug in KEYWORD_RULES:
        if any(kw in text_lower for kw in keywords):
            return slug

    return "technology"


def main() -> None:
    with SessionLocal() as db:
        # ── 1. Seed categories ────────────────────────────────────────────────
        existing_slugs = {
            row[0]
            for row in db.execute(text("SELECT slug FROM categories")).fetchall()
        }
        inserted_cats = 0
        for cat in CATEGORIES:
            if cat["slug"] not in existing_slugs:
                db.execute(
                    text(
                        "INSERT INTO categories (id, name, slug, description) "
                        "VALUES (:id, :name, :slug, :description)"
                    ),
                    {**cat, "id": str(uuid.uuid4())},
                )
                inserted_cats += 1
        db.commit()
        print(f"Categories seeded: {inserted_cats} inserted, {len(existing_slugs)} already existed")

        # ── 2. Load all problems ──────────────────────────────────────────────
        rows = db.execute(
            text("SELECT id, subreddit, title, body FROM problems WHERE category IS NULL")
        ).fetchall()
        print(f"Problems with NULL category: {len(rows)}")

        if not rows:
            print("Nothing to backfill.")
            return

        # ── 3. Backfill ───────────────────────────────────────────────────────
        counts: dict[str, int] = {}
        for row in rows:
            slug = _infer_category(row.subreddit, row.title or "", row.body)
            counts[slug] = counts.get(slug, 0) + 1
            db.execute(
                text("UPDATE problems SET category = :slug WHERE id = :id"),
                {"slug": slug, "id": row.id},
            )

        db.commit()

        print("Backfill complete:")
        for slug, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {slug:20s} {n}")


if __name__ == "__main__":
    main()
