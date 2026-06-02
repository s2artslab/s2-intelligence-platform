#!/usr/bin/env python3
"""Generate expanded BitNet specialist prompt seed file (~300+ rows)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LEGAL_ROUTING = [
    "How do I file a motion to dismiss?",
    "What is qualified immunity?",
    "Respond to a Rule 12(b)(6) motion as pro se litigant.",
    "Can I sue in federal court for civil rights violation?",
    "What is personal jurisdiction?",
    "How do I serve process on a defendant?",
    "What is a summary judgment motion?",
    "Explain discovery deadlines in litigation.",
    "What is a preliminary injunction?",
    "How do I appeal a district court order?",
    "What is standing in federal court?",
    "Draft response to motion for extension of time.",
    "What is venue in a contract dispute?",
    "How does Rule 11 sanctions work?",
    "What is a class action certification?",
]

GENERAL_ROUTING = [
    "How does vector search work in RAG?",
    "What is a REST API?",
    "Explain OAuth2 in plain terms.",
    "How do I reset my password?",
    "What is Kubernetes used for?",
    "Summarize how Stripe webhooks work.",
    "What is the difference between SQL and NoSQL?",
    "How does git rebase work?",
    "What is a CDN?",
    "Explain machine learning overfitting.",
    "How do I configure nginx reverse proxy?",
    "What is Docker used for?",
    "How does websocket differ from HTTP polling?",
    "What is prompt engineering?",
    "Explain CI/CD pipelines.",
]

TAGGING = [
    ("Client needs response by tomorrow on contract review.", "high"),
    ("Newsletter draft for next month.", "low"),
    ("Court filing due in 48 hours.", "high"),
    ("Optional blog post idea for Q3.", "low"),
    ("User reports billing double-charged.", "high"),
    ("Routine quarterly report review.", "medium"),
    ("Server down affecting production.", "high"),
    ("Ask about feature roadmap for next year.", "low"),
    ("Mediation scheduled next week.", "medium"),
    ("Internal wiki typo fix.", "low"),
]

SUMMARY = [
    "The court denied the motion without prejudice and gave 14 days to amend.",
    "Team agreed to ship the gateway fix Friday and run benchmarks over the weekend.",
    "The jury found for the plaintiff on breach of contract but not on punitive damages.",
    "Counsel requested a continuance citing incomplete discovery.",
    "The API returned 503 errors during peak load; rollback restored service.",
    "Settlement conference is set for March 12 with a confidentiality order in place.",
]

CLASSIFY = [
    ("User asks for step-by-step instructions to reset their password.", "account_help"),
    ("User wants to cancel subscription and get a refund.", "billing_cancel"),
    ("User asks what documents to attach to a civil complaint.", "legal_info"),
    ("User wants to export their chat history.", "data_export"),
    ("User reports the app is slow on mobile.", "technical_issue"),
    ("User asks how to upgrade their plan.", "billing_upgrade"),
]

CHEAP_QA = [
    "What is the capital of France?",
    "How many days are typically allowed to respond to a motion?",
    "What HTTP status code means not found?",
    "What year was the ADA enacted?",
    "What does API stand for?",
    "What is the statute of limitations?",
    "Who presides over a bench trial?",
    "What is a deposition?",
    "What is HTTPS?",
    "What is a webhook?",
]

LEGAL_COMPACT = [
    "What is a motion to dismiss?",
    "What is habeas corpus?",
    "What is qualified immunity?",
    "What is subject matter jurisdiction?",
    "What is a TRO?",
    "What is pro se representation?",
    "What is a default judgment?",
    "What is an affidavit?",
]

GENERAL_COMPACT = [
    "What is RAG in AI systems?",
    "What is a REST API?",
    "What is an egregore in this product context?",
    "What does OCR mean for PDF uploads?",
    "What is a vector database?",
    "What is fine-tuning?",
    "What is LoRA?",
    "What is a gateway API?",
]

INTENT_VARIANTS = [
    "password reset help",
    "cancel my subscription",
    "upgrade plan pricing",
    "export my data",
    "bug report slow app",
    "how to file in small claims",
    "question about court deadline",
    "invoice copy request",
    "change email address",
    "delete my account",
    "API key rotation",
    "webhook not firing",
    "refund status check",
    "schedule demo call",
    "document upload failed",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default="training_data/bitnet-specialist-prompts.json",
    )
    ap.add_argument("--merge-seed", action="store_true", help="Include existing seed file entries")
    ap.add_argument("--seed-path", default="training_data/bitnet-specialist-prompts.json")
    args = ap.parse_args()

    rows: list[dict] = []
    seen: set[str] = set()

    def add(item: dict) -> None:
        key = f"{item['task_class']}:{item['user']}"
        if key in seen:
            return
        seen.add(key)
        rows.append(item)

    if args.merge_seed:
        seed = Path(args.seed_path)
        if seed.is_file():
            for item in json.loads(seed.read_text(encoding="utf-8")):
                add(item)

    for i, text in enumerate(LEGAL_ROUTING):
        add({
            "id": f"route-legal-{i:03d}",
            "task_class": "routing",
            "context": "legal",
            "user": f"Classify as legal or general (one word only): {text}",
        })
        add({
            "id": f"route-legal-v2-{i:03d}",
            "task_class": "routing",
            "context": "legal",
            "user": f"One word — legal or general? {text}",
        })

    for i, text in enumerate(GENERAL_ROUTING):
        add({
            "id": f"route-general-{i:03d}",
            "task_class": "routing",
            "context": "general",
            "user": f"Classify as legal or general (one word only): {text}",
        })
        add({
            "id": f"route-general-v2-{i:03d}",
            "task_class": "routing",
            "context": "general",
            "user": f"One word — legal or general? {text}",
        })

    for i, (text, _exp) in enumerate(TAGGING):
        add({
            "id": f"tag-{i:03d}",
            "task_class": "tagging",
            "context": "general",
            "user": f"Tag urgency (low/medium/high): {text}",
        })
        # paraphrase variant
        add({
            "id": f"tag-v-{i:03d}",
            "task_class": "tagging",
            "context": "general",
            "user": f"Urgency level one word (low/medium/high): {text}",
        })

    for i, text in enumerate(SUMMARY):
        add({
            "id": f"summary-{i:03d}",
            "task_class": "summary",
            "context": "general",
            "user": f"Summarize in one sentence: {text}",
        })

    for i, (text, _label) in enumerate(CLASSIFY):
        add({
            "id": f"classify-{i:03d}",
            "task_class": "classification",
            "context": "general",
            "user": f"Intent label only (one or two words): {text}",
        })

    for i, text in enumerate(INTENT_VARIANTS):
        add({
            "id": f"intent-{i:03d}",
            "task_class": "classification",
            "context": "general",
            "user": f"Intent label only (one or two words): User message: {text}",
        })

    for i, text in enumerate(GENERAL_COMPACT):
        add({
            "id": f"compact-{i:03d}",
            "task_class": "compact",
            "context": "general",
            "user": f"Answer in under 40 words: {text}",
        })

    for i, text in enumerate(LEGAL_COMPACT):
        add({
            "id": f"compact-legal-{i:03d}",
            "task_class": "compact",
            "context": "legal",
            "user": f"Answer in under 40 words: {text}",
        })

    for i, text in enumerate(CHEAP_QA):
        add({
            "id": f"cheap-{i:03d}",
            "task_class": "cheap_qa",
            "context": "general",
            "user": f"One short sentence: {text}",
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} prompts -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
