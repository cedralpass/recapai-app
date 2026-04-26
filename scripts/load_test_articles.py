#!/usr/bin/env python3
"""
load_test_articles.py — Seed a test user with URLs and classify them.

Usage (from project root):
    .venv/bin/python scripts/load_test_articles.py [options]

Options:
    --username TEXT    Test user's username  [default: testuser]
    --email TEXT       Test user's email     [default: testuser@example.com]
    --password TEXT    Test user's password  [default: TestPassword123!]
    --api-url TEXT     Base URL of the recap app  [default: http://localhost:8080]
    --delay FLOAT      Seconds to wait between requests  [default: 0.5]
    --dry-run          Print URLs without submitting them
    --status           After submitting, poll until all articles are classified

Examples:
    # Basic run — creates testuser if needed, submits all URLs
    .venv/bin/python scripts/load_test_articles.py

    # Use a different base URL
    .venv/bin/python scripts/load_test_articles.py --api-url http://localhost:5000

    # Dry run to preview
    .venv/bin/python scripts/load_test_articles.py --dry-run

    # Submit and wait for classification to finish
    .venv/bin/python scripts/load_test_articles.py --status
"""

import sys
import os
import time
import argparse
import httpx

# ── Project root on sys.path so we can import the Flask app ──────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

URLS = [
    "https://heygrillhey.com/texas-style-smoked-beef-brisket/",
    "https://sqlpad.io/tutorial/flask-by-example-implementing-a-redis-task-queue/",
    "https://blog.mdturp.ch/posts/2024-04-05-visual_guide_to_vision_transformer.html",
    "https://thegradient.pub/financial-market-applications-of-llms/",
    "https://thegradient.pub/text-embedding-inversion/",
    "https://hybridhacker.email/p/my-25-year-engineering-career-retrospective?utm_source=profile&utm_medium=reader2",
    "https://paulgraham.com/greatwork.html",
    "https://arstechnica.com/science/2024/04/sleeping-more-flushes-junk-out-of-the-brain/",
    "https://medium.com/@mutahar789/optimizing-rag-a-guide-to-choosing-the-right-vector-database-480f71a33139",
    "https://www.ivp.com/content/leadership-lookback-the-4ps-of-leadership-refined-by-lessons-learned-on-the-river/",
    "https://www.ivp.com/content/from-the-battlefield-to-the-boardroom-leadership-from-4-star-general-ret-richard-d-clarke/",
    "https://lilianweng.github.io/posts/2023-06-23-agent/",
    "https://smith.langchain.com/hub/majid/chain-of-density-prompt",
    "https://barbecueathome.com/blogs/pit-masters-blog/the-meat-sweats-brisket-stall",
    "https://blog.thermoworks.com/chicken/thermal-tips-simple-roasted-chicken/",
    "https://outerbounds.com/blog/retrieval-augmented-generation/",
    "https://outerbounds.com/blog/train-dolly-metaflow/",
    "https://www.strangeloopcanon.com/p/what-can-llms-never-do",
    "https://docs.cohere.com/docs/the-cohere-platform",
    "https://github.com/tesseract-ocr/tesseract/blob/main/README.md",
    "https://kaustavmukherjee-66179.medium.com/improve-retrieval-of-documents-from-vectordb-using-maximum-marginal-relevance-mmr-for-balancing-f6ae56fb9512",
    "https://www.linkedin.com/posts/billhiggins1_recently-i-performed-a-management-exercise-activity-7190016084710764544-QTzs?utm_source=share&utm_medium=member_desktop",
    "https://www.cowboy.vc/news/ai-ification-of-unsexy-tech",
    "https://research.paulengstler.com/invisible-stitch/",
    "https://zapier.com/blog/perplexity-ai/",
    "https://cq2.co/blog/the-best-way-to-have-complex-discussions",
    "https://www.jamesshore.com/v2/blog/2024/a-useful-productivity-measure",
    "https://www.industrialempathy.com/posts/design-docs-at-google/",
    "https://www.linkedin.com/pulse/how-fine-tune-gpt-models-specific-niche-domains-solulab?utm_source=share&utm_medium=member_ios&utm_campaign=share_via",
    "https://www.datacamp.com/tutorial/fine-tuning-large-language-models",
    "https://www.datacamp.com/code-along/fine-tuning-your-own-llama-2-model",
    "https://www.fuzzylabs.ai/blog-post/llmops-in-action-finetuned-llm-models-for-legal-text-summarization",
    "https://huggingface.co/docs/transformers/en/training",
    "https://hao-ai-lab.github.io/blogs/cllm/",
    "https://levelupwithethanevans.substack.com/p/create-your-10-year-plan",
    "https://www.datacamp.com/tutorial/pytorch-vs-tensorflow-vs-keras",
    "https://www.trainerroad.com/blog/how-vo2-max-work-makes-you-fast-the-science-behind-it-all/",
    "https://tomtunguz.com/writing-separate-lines/",
    "https://tomblomfield.com/post/750852175114174464/taking-risk",
    "https://dassum.medium.com/fine-tune-large-language-model-llm-on-a-custom-dataset-with-qlora-fb60abdeba07",
    "https://www.bvp.com/atlas/why-rigorous-customer-focus-will-get-your-startup-farther-than-any-best-practice-or-playbook",
    "https://www.bvp.com/atlas/the-six-ps-of-lean-product-with-kim-caldbeck",
    "https://andrewkchan.dev/posts/diffusion.html",
    "https://sre.google/sre-book/simplicity/",
    "https://blog.bytebytego.com/p/the-scaling-journey-of-linkedin",
    "https://www.linkedin.com/pulse/ai-trust-fall-tomasz-tunguz-eervc/",
    "https://dr-arsanjani.medium.com/enhancing-the-reliability-of-llms-truth-triangulation-strategies-to-minimize-hallucinations-15f97d603b3a",
    "https://review.firstround.com/unexpected-anti-patterns-for-engineering-leaders-lessons-from-stripe-uber-carta/",
    "https://www.deeplearning.ai/the-batch/how-agents-can-improve-llm-performance/",
    "https://about.gitlab.com/blog/2024/05/30/how-gitlab-duo-helps-secure-and-thoroughly-test-ai-generated-code/",
]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--username", default="testuser")
    p.add_argument("--email",    default="testuser@example.com")
    p.add_argument("--password", default="TestPassword123!")
    p.add_argument("--api-url",  default="http://localhost:8080")
    p.add_argument("--delay",    type=float, default=0.5,
                   help="Seconds between API calls (default: 0.5)")
    p.add_argument("--dry-run",  action="store_true",
                   help="Print URLs without submitting")
    p.add_argument("--status",   action="store_true",
                   help="After submitting, poll until all articles are classified")
    return p.parse_args()


def setup_test_user(username, email, password):
    """
    Find the test user in the DB, creating them if necessary.
    Returns (user_id, api_token).
    """
    # Deferred import — needs Flask app context
    from recap import create_app, db
    import sqlalchemy as sa
    from recap.models import User

    app = create_app()
    with app.app_context():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            print(f"  Creating user '{username}' ({email}) …")
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"  User created (id={user.id})")
        else:
            print(f"  Found existing user '{username}' (id={user.id})")

        token = user.get_or_create_api_token()
        print(f"  API token: {token[:8]}…")
        return user.id, token


def poll_status(user_id, article_ids, api_base, token, poll_interval=5, timeout=600):
    """
    Poll the DB until every article in article_ids has been classified.
    Prints a summary table when done (or times out).
    """
    from recap import create_app, db
    import sqlalchemy as sa
    from recap.models import Article

    app = create_app()
    deadline = time.time() + timeout
    pending = set(article_ids)

    print(f"\nPolling for classification of {len(pending)} articles …")
    while pending and time.time() < deadline:
        with app.app_context():
            rows = db.session.scalars(
                sa.select(Article).where(Article.id.in_(pending))
            ).all()
            just_done = {r.id for r in rows if r.classified is not None}
            for r in rows:
                if r.id in just_done:
                    print(f"  [✓] id={r.id:4d}  category={r.category or '—':30s}  {r.url_path[:60]}")
        pending -= just_done
        if pending:
            print(f"  … {len(pending)} still pending — sleeping {poll_interval}s")
            time.sleep(poll_interval)

    if pending:
        print(f"\nTimeout: {len(pending)} article(s) never classified: {sorted(pending)}")
    else:
        print("\nAll articles classified.")


def print_summary(results):
    total   = len(results)
    queued  = sum(1 for r in results if r["status"] == "queued")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed  = sum(1 for r in results if r["status"] == "error")

    print(f"\n{'─'*60}")
    print(f"  Total URLs : {total}")
    print(f"  Queued     : {queued}")
    print(f"  Skipped    : {skipped}  (already in DB)")
    print(f"  Errors     : {failed}")
    print(f"{'─'*60}")

    if failed:
        print("\nFailed submissions:")
        for r in results:
            if r["status"] == "error":
                print(f"  [{r['http_status']}] {r['url'][:70]}  — {r.get('detail', '')}")


def main():
    args = parse_args()

    if args.dry_run:
        print(f"Dry run — {len(URLS)} URLs would be submitted to {args.api_url}\n")
        for i, url in enumerate(URLS, 1):
            print(f"  {i:3d}. {url}")
        return

    # ── Step 1: ensure test user exists ──────────────────────────────────────
    print("── Setting up test user ─────────────────────────────────────────")
    user_id, token = setup_test_user(args.username, args.email, args.password)

    # ── Step 2: submit URLs ───────────────────────────────────────────────────
    endpoint = f"{args.api_url.rstrip('/')}/api/v1/articles"
    headers  = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    results  = []
    article_ids = []

    print(f"\n── Submitting {len(URLS)} URLs to {endpoint} ─────────────────────────")
    with httpx.Client(timeout=30) as client:
        for i, url in enumerate(URLS, 1):
            try:
                resp = client.post(endpoint, json={"url": url}, headers=headers)
                body = resp.json()
            except Exception as exc:
                print(f"  [{i:3d}/{len(URLS)}] ERROR  {url[:65]}")
                print(f"         {exc}")
                results.append({"status": "error", "url": url, "http_status": 0, "detail": str(exc)})
                continue

            if resp.status_code == 201:
                aid = body.get("article_id")
                article_ids.append(aid)
                print(f"  [{i:3d}/{len(URLS)}] queued  id={aid}  {url[:60]}")
                results.append({"status": "queued", "url": url, "article_id": aid})
            elif resp.status_code == 409:
                # Duplicate — article already exists for this user
                print(f"  [{i:3d}/{len(URLS)}] skipped (duplicate)  {url[:55]}")
                results.append({"status": "skipped", "url": url, "http_status": 409})
            else:
                print(f"  [{i:3d}/{len(URLS)}] ERROR {resp.status_code}  {url[:60]}")
                print(f"         {body}")
                results.append({"status": "error", "url": url, "http_status": resp.status_code,
                                 "detail": str(body)})

            if i < len(URLS):
                time.sleep(args.delay)

    print_summary(results)

    # ── Step 3 (optional): wait for classification ────────────────────────────
    if args.status and article_ids:
        poll_status(user_id, article_ids, args.api_url, token)


if __name__ == "__main__":
    main()
