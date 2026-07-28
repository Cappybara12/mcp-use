#!/usr/bin/env python3
"""
Wayzyy Article Writer — end-to-end article generation agent.

Usage:
  python main.py                          # interactive — pick from pending topics
  python main.py --topic "Tambdi Surla Temple Goa"
  python main.py --outline ../24-7-chronically-online/review/2026-07-07_firecrawl-vs-apify.md
  python main.py --list                   # show pending topics from review/
"""

import argparse
import os
import sys
import re
import yaml
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_pending_topics() -> list[dict]:
    """Load approved/pending outlines from 24-7-chronically-online/review/."""
    review_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "24-7-chronically-online", "review"
    )

    topics = []
    if not os.path.exists(review_dir):
        return topics

    for fname in sorted(os.listdir(review_dir)):
        if not fname.endswith(".md"):
            continue

        fpath = os.path.join(review_dir, fname)
        with open(fpath) as f:
            content = f.read()

        # Parse frontmatter
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            try:
                fm = yaml.safe_load(fm_match.group(1))
                status = fm.get("status", "pending_review")
                if status in ("pending_review", "approved"):
                    keyword = fm.get("keyword", fname)
                    topics.append({
                        "keyword": keyword,
                        "file": fpath,
                        "status": status,
                        "classification": fm.get("classification", ""),
                        "source_count": fm.get("source_count", 0),
                    })
            except Exception:
                pass

    return topics


def pick_topic_interactive(topics: list[dict]) -> str:
    """Show pending topics and let user pick one or enter a new one."""

    print("\n" + "="*60)
    print("WAYZYY ARTICLE WRITER")
    print("="*60)

    if topics:
        print(f"\nPending topics from review queue ({len(topics)}):\n")
        for i, t in enumerate(topics, 1):
            badge = "★" if t["status"] == "approved" else "○"
            print(f"  {i}. {badge} {t['keyword']}  [{t['classification']}] ({t['source_count']} sources)")
        print()

    print("  Enter a number to pick from the list above")
    print("  Or type a new topic directly (e.g. 'Tambdi Surla Temple Goa Guide')")
    print("  Or press [q] to quit\n")

    choice = input("Your choice: ").strip()

    if choice.lower() == "q":
        print("Bye!")
        sys.exit(0)

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(topics):
            return topics[idx]["keyword"]
        else:
            print("Invalid number. Please try again.")
            return pick_topic_interactive(topics)
    else:
        return choice


def slugify(text: str) -> str:
    """Convert topic to filename slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def save_draft(title: str, article: str, topic: str) -> str:
    """Save the finished article to drafts/."""
    drafts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drafts")
    os.makedirs(drafts_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(topic)
    filename = f"{date_str}_{slug}.md"
    filepath = os.path.join(drafts_dir, filename)

    with open(filepath, "w") as f:
        f.write(article)

    return filepath


def check_env():
    """Verify required API keys are present."""
    required = {
        "GROQ_API_KEY": "Already in your 24-7-chronically-online .env",
        "FIRECRAWL_API_KEY": "Already in your 24-7-chronically-online .env",
    }

    missing = []
    for key, source in required.items():
        if not os.environ.get(key):
            missing.append(f"  {key} — {source}")

    if missing:
        print("\n[error] Missing API keys in .env:\n")
        for m in missing:
            print(m)
        print("\nCopy .env.example to .env and fill in the keys.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Wayzyy Article Writer")
    parser.add_argument("--topic", type=str, help="Topic to write about")
    parser.add_argument("--outline", type=str, help="Path to existing outline .md file")
    parser.add_argument("--list", action="store_true", help="List pending topics and exit")
    parser.add_argument("--skip-research", action="store_true", help="Skip research step (use cached or manual brief)")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve outline without prompting (for testing)")
    args = parser.parse_args()

    check_env()

    # List mode
    if args.list:
        topics = load_pending_topics()
        if topics:
            print(f"\nPending topics ({len(topics)}):\n")
            for t in topics:
                print(f"  • {t['keyword']} [{t['status']}]")
        else:
            print("No pending topics found in review/")
        return

    # Determine topic
    topic = args.topic

    if args.outline:
        # Read topic from outline file
        with open(args.outline) as f:
            content = f.read()
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            fm = yaml.safe_load(fm_match.group(1))
            topic = fm.get("keyword", topic)
        print(f"[main] Using outline file. Topic: {topic}")

    if not topic:
        topics = load_pending_topics()
        topic = pick_topic_interactive(topics)

    print(f"\n[main] Writing article for: '{topic}'")
    print("-"*60)

    # Step 1: Research
    research_brief = ""
    if not args.skip_research:
        print("\n[Step 1/4] Researching topic via Firecrawl + Gemini...")
        from agent.researcher import run_research
        research_result = run_research(topic)
        research_brief = research_result["brief"]
        if research_result["status"] == "failed":
            print("[main] Research failed — continuing with limited context.")
    else:
        print("[Step 1/4] Skipping research (--skip-research flag set)")
        research_brief = f"Topic: {topic}. Write a comprehensive Goa travel guide based on your knowledge."

    # Step 2: Plan outline
    print("\n[Step 2/4] Generating outline...")
    from agent.planner import generate_outline, show_and_confirm_outline
    outline_text = None

    while outline_text is None:
        draft_outline = generate_outline(topic, research_brief)
        if args.auto_approve:
            print(draft_outline)
            outline_text = draft_outline
        else:
            outline_text = show_and_confirm_outline(draft_outline)
            if outline_text is None:
                print("[main] Regenerating outline...")

    # Step 3: Write article section by section
    print("\n[Step 3/4] Writing article section by section...")
    from agent.writer import parse_outline, write_full_article

    parsed = parse_outline(outline_text)
    if not parsed["title"]:
        parsed["title"] = topic
    if not parsed["primary_keyword"]:
        parsed["primary_keyword"] = topic

    article = write_full_article(parsed, research_brief)

    # Step 4: Style check
    print("\n[Step 4/4] Running style check...")
    from agent.style_checker import check_article, print_style_report

    result = check_article(article)
    print_style_report(result)
    article = result["article"]

    # Save draft
    filepath = save_draft(parsed["title"], article, topic)
    print(f"\n✓ Draft saved to: {filepath}")
    print(f"  Word count: {result['word_count']}")

    if result["flags"]:
        high_flags = [f for f in result["flags"] if f["severity"] == "HIGH"]
        if high_flags:
            print(f"\n  ⚠ {len(high_flags)} HIGH priority issues need manual review before publishing.")
        else:
            print(f"\n  {len(result['flags'])} minor issues flagged — review when ready.")

    print("\nDone. Open the draft, do a quick read, and it's ready to publish. 🎯")


if __name__ == "__main__":
    main()
