# Pipeline Studio

A visual editor for content pipelines, in the style of n8n: boxes (steps) joined by lines, run with one
click, each step showing its result as it finishes. It sits on top of the same Python receiver and
Graftcode setup as the rest of this project.

```
Topic ─┬─► Keyword research ─┐
RSS ───┤                     ├─► Outline ─► Write ─► SEO check ─► Human review ─┬─► Reddit post ideas
Web research ────────────────┘                                                  └─► Publish (GitHub PR)
Learn from your blog ─► Rulebook ──────────────┘
```

Start it with `bash scripts/start.sh`, open <http://localhost:5173> and use **Pipeline**. A first-time
install creates a **Demo blog** workspace that works fully offline: sample feeds, a sample blog to learn
from, and an offline "Demo" AI that writes clearly labelled template text. Nothing needs an API key until
you choose a real provider.

## The screens

| Screen | What it does |
|---|---|
| **Pipeline** | Drag steps from the left onto the canvas and connect them. Type a topic (or pick a plan item), press **Run pipeline**: steps light up as they run and stop at **Human review**. Click any step to change its settings, write your own instructions, pick its AI provider, model and API key, preview the exact prompt, or re-run it. Edits save automatically. |
| **Content planner** | A library of ideas on the left (from RSS, keyword research, or typed in), grouped by category. Drag an idea onto a day to schedule it. Click an item to set the date and time, keyword, category and notes, or press **Create draft now**. **Schedule on GitHub** produces a workflow that does this on a timer. |
| **Rulebook** | The rules your blog follows, learned from your existing posts, each with the evidence behind it ("11 of 14 posts open with a question"). Switch rules off, reword them, or add your own. |
| **Settings & keys** | Per workspace: blog address, voice, categories, default AI, GitHub target, your Reddit playbook, and the API key manager. |

A **workspace** is one blog or organization. Each has its own keys, rulebook, plan, ideas and pipelines, so
one person can manage several.

## The steps

| Step | What it does | Needs a key? |
|---|---|---|
| Topic | The article to write, from a plan item or typed in. | No |
| RSS feeds | Fetches headlines, adds them to your idea library. | No |
| Web research | Searches the web and reads the top pages. | TinyFish (optional; "Direct fetch" is free) |
| Learn from your blog | Reads your published posts and measures how you write. | No (TinyFish optional for JavaScript-heavy sites) |
| Rulebook | Supplies your rules and voice to the writing steps. | No |
| Keyword research | Finds keywords and picks a primary one. | DataForSEO or TinyFish (optional; "Manual" is free) |
| Outline / Write draft | AI steps. Each has a prompt box for your own instructions. | An AI provider key (or the offline Demo AI) |
| SEO check | Scores the draft (title, headings, keyword use, links, meta description, FAQ) and builds FAQ schema. | No |
| Human review | Pauses the run so a person reads, edits, and approves or rejects. | No |
| Reddit post ideas | Drafts Reddit posts that promote the article without spamming, following **your** playbook. Pick a kind of post: discussion, contrarian take, comparison with a table, comparison with competitors, how-to, or feedback request. Add a disclosure line that is put at the top of every draft. Warns about missing disclosures, vote requests, "DM me", links in titles and unsourced competitor claims. It never posts anything; you post from your own authorized accounts. | An AI provider key (or Demo AI) |
| Publish | Opens a GitHub pull request with the approved article. Never merges. Defaults to a dry run. | GitHub token (for real PRs) |

Every AI step (and the workspace as a whole) has a **prompt box**. The prompt each AI step sends is built from
your instructions, the rulebook, the keywords, the research and the outline, and you can see it with
**Preview prompt** before spending anything.

## Learning how you write

The **Learn from your blog** step reads up to 30 posts (found from a feed, a sitemap, or URLs you paste) and
**measures** them. Nothing is guessed:

- length, headings, how long sentences are, reading ease
- em dash use per 1,000 words
- how posts open (question, number, story, claim), and whether there is a hook
- FAQ sections and whether the page publishes FAQPage JSON-LD schema
- title patterns (numbers, year, colon), lists, external links, how posts end
- phrases that recur across posts

It turns these into plain rules, each with its evidence, saved to your rulebook. Rules are used twice: they are
added to the writing prompts, and every draft is checked against them in the SEO step. Re-learning keeps your
choices: rules you switched off, reworded, or added stay that way.

## Providers

| Provider | Used for | Notes |
|---|---|---|
| OpenAI, Anthropic, Groq, Moonshot (Kimi), OpenRouter | Outline, Write, Reddit | Pick a provider and model per step, or set a workspace default. |
| Demo | Same steps, offline | Template text, not AI. For trying the flow and for tests. |
| [TinyFish](https://docs.tinyfish.ai) Search and Fetch | Web research, keyword ideas from what ranks, reading blogs | Per its docs, Search and Fetch are free within a daily allowance; check current limits. |
| [DataForSEO](https://docs.dataforseo.com) | Keyword suggestions with volume, difficulty and intent | Pay as you go. This is the same data source [OpenSEO](https://github.com/every-app/open-seo) is built on. Studio calls DataForSEO directly, so OpenSEO itself is not required. |
| GitHub | Publish (pull request) | A token with access to the repo. |

You can keep **several keys** (name them) and choose which one each step uses, or set one default per
workspace. For DataForSEO, paste the Base64 value from its API Access page (what OpenSEO calls
`DATAFORSEO_API_KEY`) or `login:password`.

> **What has and has not been verified.** The offline flow, the engine, the rulebook learning, the SEO checks,
> scheduling, the exports and the UI are tested end to end (256 automated tests, plus a click-through of the
> dashboard in a browser). The calls to OpenAI, Anthropic, Groq, Moonshot, OpenRouter, TinyFish, DataForSEO and
> GitHub are tested against mock servers that follow each provider's published API documentation. They have
> **not** been run against the real services with real accounts. Try each with a small test before relying on it.

## Scheduling

Dragging an item onto a day sets when its draft should be created. Two ways to make that happen:

1. **From the dashboard:** **Create drafts that are due** runs every plan item whose time has passed.
2. **On a timer, with a GitHub Action:** **Schedule on GitHub** produces a workflow file and the workspace
   files (settings, plan, rulebook, pipelines; never API keys). Commit them to your site repository and add
   the listed secrets. The workflow runs `graft-studio run-due`, which creates drafts and opens a **pull
   request** for you to review. Nothing is published until you merge it.

Runs started by the scheduler stop at the review step, exactly like manual runs. In CI, a named key
can be supplied as the environment variable `STUDIO_KEY_SLOT_<NAME>`, or by provider as `STUDIO_KEY_<PROVIDER>`.

## Use it from Claude or Cursor (MCP)

The Graftcode Gateway serves every Studio method as an MCP tool at `http://localhost:8081/mcp` (see the
README for the Cursor and Claude Desktop setup). Two tools do the whole job in one call each:

| Tool | What it does |
|---|---|
| `studio_write_article(ws, topic, keyword)` | Runs the workspace's pipeline for a topic up to human review and returns the draft, the SEO score, what to fix, and a `run_id`. |
| `studio_decide(ws, run_id, decision, notes, publish)` | Approves or rejects that draft. Approving also runs the remaining steps (Reddit ideas). It runs the Publish step **only if `publish` is true**. |

For example: *"List my workspaces, write an article on 'how to read a retention table' with the keyword
'retention table' in demo-blog, and tell me what the SEO check wants fixed."* Then, after you have read the
draft: *"Approve it, don't publish."*

Everything else is available too: list workspaces and plan items, add ideas, read and edit the rulebook, preview
prompts, create and run pipelines step by step, and export the GitHub Action.

Things to know:

- **Approval is yours.** The tool descriptions tell the assistant to wait for your explicit decision, but nothing
  technical stops an assistant from calling `studio_decide`. Treat it like any tool you give an assistant.
- **Admin tools are exposed too**, including deleting a workspace and saving API keys. Anything that can reach the
  gateway can call them; the gateway has no authentication. Keep it on localhost.
- With about 48 tools, some assistants work better if you tell them which two to use.

## Security model

- **API keys** are stored on your computer in `~/.graft-studio` (override with `STUDIO_DATA_DIR`), outside
  this repository, with owner-only file permissions. They are **write-only**: no method returns a key, only a
  masked tail (`••••6789`). Provider error messages are scrubbed so a key never reaches the screen, logs or the
  saved run. Keys are only ever sent to the provider they belong to.
- **Fetching URLs you supply** (feeds, blog pages) is protected against server-side request forgery: only
  http(s), no embedded credentials, the host is resolved once and every address must be public, and the
  connection is pinned to the address that was checked (so DNS rebinding cannot swap it). Redirects are
  re-checked at every hop, responses are size-limited, and feeds that declare XML entities are rejected.
- **Identifiers and paths** (workspace, pipeline, run, rule and plan ids) are validated, and every file
  path is confirmed to stay inside the data folder.
- **AI output and scraped text are untrusted:** the dashboard renders markdown without `innerHTML` and only
  makes http(s) links clickable.
- **Publishing needs a person.** The Publish step refuses to run until a human has approved the draft. It
  opens a pull request and never merges.
- **The gateway has no authentication.** Anything that can reach it can call every method, including the
  Studio's, and the Studio methods are also exposed as MCP tools. Keep it on localhost (the default) or put
  authentication in front of it before exposing it.

## Extending it

A step is a function plus a form definition, in `receiver/article_receiver/studio/nodes.py`:

```python
def run_my_step(ctx, config, upstream):
    ...                      # ctx.key(provider), ctx.llm(...), ctx.cfg; upstream = outputs of earlier steps
    return {"my_output": ...}

NODE_TYPES["my_step"] = {"label": "My step", "group": "Custom", "description": "...",
                         "run": run_my_step, "defaults": {}, "fields": [{"key": "x", "label": "X", "type": "text"}]}
```

The dashboard builds the settings form from `fields`, and the palette, saving and run engine pick the step up
automatically. Add a result view in `ui/src/studio/OutputView.tsx` if it needs more than the generic one.

## Files

```
receiver/article_receiver/studio/
  store.py      workspaces, keys, pipelines, plan, rulebook, runs (validated, atomic writes)
  net.py        SSRF-safe fetching, keyed API calls, error scrubbing
  providers.py  LLMs, TinyFish, DataForSEO, GitHub
  docs.py       HTML and markdown into structure          rulebook.py  learning and checking rules
  seo.py        SEO checks, FAQ schema                    sources.py   feeds, blog discovery, samples
  nodes.py      the steps                                 engine.py    running a pipeline
  scheduler.py  due items, GitHub Action export           cli.py       graft-studio run-due
  api.py        what the dashboard calls
ui/src/studio/   the dashboard screens
receiver/tests/studio/   the tests
```
