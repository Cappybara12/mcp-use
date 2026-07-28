# Article Writer MCP

An MCP server that runs a full content pipeline from Claude chat: finds
trending topics in your niche, researches them for real facts, writes a
full article in your brand voice, sources a licensed image, and can push
the finished piece straight to your website's GitHub repo as a pull request.

Built for [Wayzyy](https://wayzyy.com), a Goa vacation rental marketplace —
but the brand-specific bits are pulled into `config.yaml` so you can point
this at your own blog/niche.

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your API keys (Kimi, Groq, Firecrawl, Pexels)
3. Edit `config.yaml` with your own brand name, blog URL, and site repo path
4. Register the server in your Claude Desktop config, pointing at `mcp_server.py`

## What's genericized vs. what still needs work

`config.yaml` covers the structural stuff — brand name, blog URL, contact
email, niche, and the closing CTA wording. That's enough to get the pipeline
running for a different site without touching Python code.

**Not yet genericized:** the deeper brand-voice content in `prompts/style_guide.py`
and `prompts/article_format.py` (banned phrases, tone rules, article structure
templates) and the site-specific TSX conversion logic in `agent/site_publisher.py`
(built against Wayzyy's exact Vite/React blog format — a different site's blog
will need its own version of that converter). Treat those as the files to
rewrite for your own brand/site.

## Tools

- `run_scanner` — find trending topics via Google News RSS, deduped against what you've already published
- `suggest_next_article` — ranked recommendations with real evidence
- `write_article` — full pipeline: research → outline → write → image → style check → save
- `get_draft` / `preview_draft` / `open_draft` — review the draft (text, rendered localhost page, or a real editor)
- `run_style_check` — quality report
- `edit_draft` — request changes, rewritten and saved automatically
- `save_draft` — save edited text directly, no LLM call needed
- `push_to_github` — converts to your site's format and opens a real PR for review
