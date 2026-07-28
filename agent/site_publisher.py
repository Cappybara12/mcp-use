"""
Converts an approved article draft into the wayzyy-site repo's real blog
post format (React/TSX + BlogLayout), then commits it to a new branch and
pushes — never to main directly. You always review the actual PR before
anything goes live.

Site pattern (5 coordinated pieces per post), confirmed against
src/pages/blog/BestTimeToVisitGoa.tsx and src/lib/blogPosts.ts:
  1. src/pages/blog/{Component}.tsx   — the post itself
  2. src/lib/blogPosts.ts             — metadata entry (title, SEO meta, hero image, date)
  3. src/App.tsx                      — import + <Route> registration
  4. public/sitemap.xml               — new <url> entry
  5. public/blog/{slug}-hero.jpg      — real image file, not an external link
"""

import os
import re
import glob
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

from agent.config import load_config

_cfg = load_config()
WAYZYY_SITE_DIR = Path(_cfg["site_repo_path"])
BRAND_NAME = _cfg["brand"]["name"]
BLOG_URL = _cfg["brand"]["blog_url"]


def _find_ssh_auth_sock() -> str | None:
    """MCP servers launched by Claude Desktop don't inherit SSH_AUTH_SOCK from
    an interactive shell, so `git push` over SSH fails with 'Permission denied
    (publickey)' even though the key is loaded and works fine from Terminal.
    The socket still exists on disk though — find the live one at runtime
    (its path has a random per-login-session component, so it can't be
    hardcoded and will change across reboots/re-logins)."""
    for path in glob.glob("/var/run/com.apple.launchd.*/Listeners"):
        if os.path.exists(path):
            return path
    return None


# ─── Markdown parsing ──────────────────────────────────────────────────────

def parse_draft(article_text: str) -> dict:
    """Parse our written draft's markdown into a structure ready for JSX."""
    lines = article_text.strip().split("\n")

    result = {"title": "", "intro": [], "sections": [], "faq": [], "final_thoughts": []}
    current_section = None
    current_h3 = None
    mode = "pre-title"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("# ") and not result["title"]:
            result["title"] = line[2:].strip()
            mode = "intro"
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            if "frequently asked" in heading.lower() or "faq" in heading.lower():
                mode = "faq"
                continue
            if "final thoughts" in heading.lower():
                mode = "final"
                continue
            current_section = {"heading": heading, "paragraphs": [], "subsections": []}
            result["sections"].append(current_section)
            current_h3 = None
            mode = "section"
            continue

        if line.startswith("### ") and current_section is not None:
            current_h3 = {"heading": line[4:].strip(), "paragraphs": []}
            current_section["subsections"].append(current_h3)
            continue

        if line.startswith("---") or line.startswith("*Looking for a villa") or line.startswith("*Want to list"):
            continue  # skip the hardcoded CTA lines — BlogLayout/site has its own CTA pattern

        # FAQ entries: **Question** on one line, answer on next non-empty line
        if mode == "faq":
            if line.startswith("**") and line.endswith("**"):
                result["faq"].append({"q": line.strip("*").strip(), "a": ""})
            elif result["faq"]:
                result["faq"][-1]["a"] += (" " if result["faq"][-1]["a"] else "") + line
            continue

        if mode == "final":
            result["final_thoughts"].append(line)
            continue

        if mode == "intro":
            result["intro"].append(line)
        elif mode == "section":
            if current_h3 is not None:
                current_h3["paragraphs"].append(line)
            else:
                current_section["paragraphs"].append(line)

    return result


def markdown_inline_to_jsx(text: str) -> str:
    """Convert inline markdown (bold, links) to JSX. Escapes curly braces
    since JSX treats { } as expression boundaries."""
    text = text.replace("{", "&#123;").replace("}", "&#125;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = text.replace('"', "&quot;") if False else text  # keep quotes as-is inside JSX text nodes, safe
    return text


# ─── TSX generation ────────────────────────────────────────────────────────

def slug_to_component_name(slug: str) -> str:
    parts = re.split(r"[-_]", slug)
    return "".join(p.capitalize() for p in parts)


def get_existing_slugs() -> set[str]:
    path = WAYZYY_SITE_DIR / "src" / "lib" / "blogPosts.ts"
    content = path.read_text()
    return set(re.findall(r'slug:\s*"([^"]+)"', content))


def make_unique_slug(base_slug: str, hint: str) -> str:
    """If base_slug already exists on the site, disambiguate using a word
    from the full title (hint) rather than silently colliding — a slug
    collision means the site's blogPosts.find() would show the WRONG
    article's data on this page (verified: this actually happened in
    testing — two different draft topics converged on the same core slug)."""
    existing = get_existing_slugs()
    if base_slug not in existing:
        return base_slug

    hint_words = re.sub(r"[^a-z0-9\s]", "", hint.lower()).split()
    base_words = set(base_slug.split("-"))
    extra = next((w for w in hint_words if w not in base_words and len(w) > 3), None)
    candidate = f"{base_slug}-{extra}" if extra else f"{base_slug}-2"

    n = 2
    while candidate in existing:
        candidate = f"{base_slug}-{extra or 'guide'}-{n}"
        n += 1
    return candidate


def generate_tsx(slug: str, parsed: dict, hero_image_alt: str) -> str:
    component_name = slug_to_component_name(slug)

    body_parts = []
    for p in parsed["intro"]:
        body_parts.append(f"      <p>\n        {markdown_inline_to_jsx(p)}\n      </p>")

    for section in parsed["sections"]:
        body_parts.append(f'      <h2>{markdown_inline_to_jsx(section["heading"])}</h2>')
        for p in section["paragraphs"]:
            body_parts.append(f"      <p>\n        {markdown_inline_to_jsx(p)}\n      </p>")
        for sub in section["subsections"]:
            body_parts.append(f'      <h3>{markdown_inline_to_jsx(sub["heading"])}</h3>')
            for p in sub["paragraphs"]:
                body_parts.append(f"      <p>\n        {markdown_inline_to_jsx(p)}\n      </p>")

    if parsed["faq"]:
        body_parts.append('      <h2>Frequently Asked Questions</h2>')
        for item in parsed["faq"]:
            body_parts.append(f'      <h3>{markdown_inline_to_jsx(item["q"])}</h3>')
            body_parts.append(f'      <p>\n        {markdown_inline_to_jsx(item["a"])}\n      </p>')

    if parsed["final_thoughts"]:
        body_parts.append('      <h2>Final Thoughts</h2>')
        for p in parsed["final_thoughts"]:
            body_parts.append(f"      <p>\n        {markdown_inline_to_jsx(p)}\n      </p>")

    body = "\n".join(body_parts)

    faq_json_ld = ""
    if parsed["faq"]:
        entries = []
        for item in parsed["faq"]:
            q = item["q"].replace('"', '\\"')
            a = item["a"].replace('"', '\\"')
            entries.append(
                '    {\n'
                '      "@type": "Question",\n'
                f'      name: "{q}",\n'
                '      acceptedAnswer: {\n'
                '        "@type": "Answer",\n'
                f'        text: "{a}",\n'
                '      },\n'
                '    },'
            )
        faq_json_ld = (
            "const faqJsonLd = {\n"
            '  "@context": "https://schema.org",\n'
            '  "@type": "FAQPage",\n'
            "  mainEntity: [\n" + "\n".join(entries) + "\n  ],\n};\n\n"
        )

    extra_jsonld_prop = "\n      extraJsonLd={faqJsonLd}" if parsed["faq"] else ""

    return f"""import {{ BlogLayout }} from "@/components/BlogLayout";
import {{ blogPosts }} from "@/lib/blogPosts";

const post = blogPosts.find((p) => p.slug === "{slug}")!;

{faq_json_ld}export default function {component_name}() {{
  return (
    <BlogLayout
      title={{post.title}}
      description={{post.description}}
      metaTitle={{post.metaTitle}}
      metaDescription={{post.metaDescription}}
      heroImage={{post.heroImage}}
      heroImageAlt="{hero_image_alt}"
      publishedDate={{post.publishedDate}}
      slug={{post.slug}}{extra_jsonld_prop}
    >
{body}
    </BlogLayout>
  );
}}
"""


# ─── SEO metadata ──────────────────────────────────────────────────────────

def make_seo_meta(title: str, core_topic: str) -> dict:
    """metaTitle <=60 chars, metaDescription <=155 chars — per BlogLayout's own convention.
    core_topic should be the clean topic (e.g. "Where to Stay in Goa"), not the
    full flowery title with subtitle — avoids truncating mid-subtitle into "...".
    """
    year = datetime.now().year
    meta_title = f"{core_topic} ({year}) — Complete Guide"
    if len(meta_title) > 60:
        meta_title = core_topic if len(core_topic) <= 60 else core_topic[:60].rsplit(" ", 1)[0]

    topic_lower = core_topic.lower()
    location_clause = "" if "goa" in topic_lower else " in Goa"
    description = f"{core_topic}{location_clause} — practical tips, real costs, and honest advice for {year}."
    if len(description) > 155:
        description = description[:152].rsplit(" ", 1)[0] + "."
    return {"metaTitle": meta_title, "metaDescription": description}


# ─── Images ─────────────────────────────────────────────────────────────────

def download_hero_image(url: str, slug: str) -> str:
    """Download the Pexels hero image into public/blog/, return the site-relative path."""
    ext = ".jpg"
    dest_dir = WAYZYY_SITE_DIR / "public" / "blog"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{slug}-hero{ext}"
    if dest_path.exists():
        raise FileExistsError(f"{dest_path} already exists — refusing to overwrite.")

    r = requests.get(url, timeout=20)
    r.raise_for_status()
    dest_path.write_bytes(r.content)

    return f"/blog/{slug}-hero{ext}"


# ─── Repo file edits ────────────────────────────────────────────────────────

def add_blog_post_entry(slug: str, title: str, description: str, meta_title: str,
                         meta_description: str, hero_image: str, read_time: str) -> None:
    path = WAYZYY_SITE_DIR / "src" / "lib" / "blogPosts.ts"
    content = path.read_text()

    entry = f'''  {{
    slug: "{slug}",
    title: "{title}",
    description:
      "{description}",
    metaTitle: "{meta_title}",
    metaDescription:
      "{meta_description}",
    heroImage: "{hero_image}",
    publishedDate: "{datetime.now().strftime("%Y-%m-%d")}",
    readTime: "{read_time}",
  }},
'''
    # Insert right before the closing "];" of the blogPosts array
    idx = content.rstrip().rfind("];")
    new_content = content[:idx] + entry + content[idx:]
    path.write_text(new_content)


def add_app_route(slug: str, component_name: str) -> None:
    path = WAYZYY_SITE_DIR / "src" / "App.tsx"
    content = path.read_text()

    import_line = f'import {component_name} from "./pages/blog/{component_name}";\n'
    route_line = f'              <Route path="/blog/{slug}" element={{<{component_name} />}} />\n'

    # Insert import after the last blog import
    last_blog_import = list(re.finditer(r'^import \w+ from "\./pages/blog/\w+";\n', content, re.MULTILINE))
    if last_blog_import:
        insert_at = last_blog_import[-1].end()
        content = content[:insert_at] + import_line + content[insert_at:]

    # Insert route after the last blog route
    last_blog_route = list(re.finditer(r'^\s*<Route path="/blog/[\w-]+".*?/>\n', content, re.MULTILINE))
    if last_blog_route:
        insert_at = last_blog_route[-1].end()
        content = content[:insert_at] + route_line + content[insert_at:]

    path.write_text(content)


def add_sitemap_entry(slug: str) -> None:
    path = WAYZYY_SITE_DIR / "public" / "sitemap.xml"
    content = path.read_text()

    entry = f'''  <url>
    <loc>{BLOG_URL}/blog/{slug}</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
'''
    idx = content.rstrip().rfind("</urlset>")
    new_content = content[:idx] + entry + content[idx:]
    path.write_text(new_content)


# ─── Git ────────────────────────────────────────────────────────────────────

def _run_git(args: list[str]) -> str:
    env = os.environ.copy()
    if "SSH_AUTH_SOCK" not in env:
        sock = _find_ssh_auth_sock()
        if sock:
            env["SSH_AUTH_SOCK"] = sock

    result = subprocess.run(
        ["git"] + args, cwd=WAYZYY_SITE_DIR, capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def branch_exists(branch: str) -> bool:
    """Check both local and remote — a real bug here caused a messy partial
    stash-pop failure during testing when the same slug was pushed twice."""
    local = _run_git(["branch", "--list", branch]).strip()
    remote = _run_git(["ls-remote", "--heads", "origin", branch]).strip()
    return bool(local or remote)


def commit_and_push(slug: str, title: str) -> str:
    """Commits everything on a new branch and pushes. Returns the GitHub
    compare URL — nothing gets merged without you clicking through and
    opening the PR yourself.

    Always syncs local main to origin/main first — every new post touches
    the same 3 shared files (blogPosts.ts, App.tsx, sitemap.xml) at the same
    insertion point, so branching from a stale main causes a guaranteed merge
    conflict the moment an earlier PR merges before this one does (confirmed:
    this exact conflict happened in testing when a second branch was created
    before the first PR had been merged back)."""
    _run_git(["fetch", "origin"])

    branch = f"add-blog-{slug}"
    if branch_exists(branch):
        raise RuntimeError(
            f"Branch '{branch}' already exists (locally or on GitHub) — this topic was "
            f"likely already pushed. Check the existing PR, or delete that branch first "
            f"if you really want to re-push."
        )

    _run_git(["checkout", "main"])
    _run_git(["pull", "--ff-only", "origin", "main"])
    _run_git(["checkout", "-b", branch])
    try:
        _run_git(["add", "-A"])
        _run_git(["commit", "-m", f"Add blog post: {title}"])
        _run_git(["push", "-u", "origin", branch])
    finally:
        _run_git(["checkout", "main"])

    remote_url = _run_git(["remote", "get-url", "origin"]).strip()
    # git@github.com:owner/repo.git -> owner/repo
    match = re.search(r"github\.com[:/](.+?)(\.git)?$", remote_url)
    repo = match.group(1) if match else "wayzyy-project/wayzyy-site"
    return f"https://github.com/{repo}/compare/main...{branch}?expand=1"


# ─── Orchestration ──────────────────────────────────────────────────────────

def publish_draft(draft_path: str, dry_run: bool = False) -> dict:
    """Full pipeline: parse draft -> generate TSX -> download image ->
    update blogPosts.ts/App.tsx/sitemap.xml -> (if not dry_run) commit + push.
    dry_run=True writes all the files so you can inspect them, but skips git
    entirely — nothing touches the repo's history until you're ready.

    Safety: if there's already unrelated uncommitted work sitting on the repo
    (e.g. a different in-progress post), it gets stashed before we touch
    anything and restored onto main afterward — otherwise `git add` would
    bundle that unrelated work into this push, which isn't what was asked for.
    """
    from pathlib import Path as _Path
    import re as _re

    # Parsing is pure text — no git touched yet. Compute the slug and check
    # for a colliding branch BEFORE stashing or writing anything, so a repeat
    # push attempt fails immediately and cleanly instead of leaving the repo
    # in a half-applied state (a real failure mode hit during testing).
    article_text = _Path(draft_path).read_text()
    parsed = parse_draft(article_text)
    title = parsed["title"]
    # Our titles follow "[Topic] (Year): [Subtitle]" — slug from just the
    # topic part, not the whole flowery title, matching the site's existing
    # clean slugs (e.g. "best-time-to-visit-goa", not a full sentence).
    core = title.split(":")[0]
    core = _re.sub(r"\(\d{4}\)", "", core).strip()
    base_slug = _re.sub(r"[^a-z0-9]+", "-", core.lower()).strip("-")
    slug = make_unique_slug(base_slug, title)
    component_name = slug_to_component_name(slug)

    if not dry_run and branch_exists(f"add-blog-{slug}"):
        raise RuntimeError(
            f"Branch 'add-blog-{slug}' already exists — this topic was likely already "
            f"pushed. Check for an existing PR before retrying."
        )

    stashed = False
    if not dry_run:
        status = _run_git(["status", "--porcelain"])
        if status.strip():
            _run_git(["stash", "-u", "-m", "site_publisher: auto-stash pre-existing work"])
            stashed = True

    from agent.images import get_hero_image
    hero = get_hero_image(f"{title} Goa")
    hero_image_path = "/blog/placeholder-hero.jpg"
    hero_alt = title
    if hero:
        hero_image_path = download_hero_image(hero["url"], slug)
        hero_alt = hero["alt"]

    seo = make_seo_meta(title, core)
    description = seo["metaDescription"]

    tsx_content = generate_tsx(slug, parsed, hero_alt)
    tsx_path = WAYZYY_SITE_DIR / "src" / "pages" / "blog" / f"{component_name}.tsx"
    if tsx_path.exists():
        # Hard stop, not just a slug-uniqueness check — this caught a real
        # near-miss during testing where a generated component name collided
        # with an existing published page and silently overwrote it.
        raise FileExistsError(
            f"{tsx_path} already exists — refusing to overwrite. "
            f"This usually means the slug/component-name collision check upstream "
            f"missed something; pick a different topic title or investigate before retrying."
        )
    tsx_path.write_text(tsx_content)

    add_blog_post_entry(slug, title, description, seo["metaTitle"], seo["metaDescription"], hero_image_path, "8 Min Read")
    add_app_route(slug, component_name)
    add_sitemap_entry(slug)

    result = {
        "slug": slug,
        "component_name": component_name,
        "tsx_path": str(tsx_path),
        "hero_image_path": hero_image_path,
    }

    if not dry_run:
        try:
            result["pr_url"] = commit_and_push(slug, title)
        finally:
            if stashed:
                _run_git(["stash", "pop"])

    return result
