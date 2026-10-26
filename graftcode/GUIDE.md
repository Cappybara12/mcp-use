# Getting started: a step-by-step guide

This guide takes you from nothing to your first AI-written, SEO-checked article that you approve before
anything is published. It takes about 15 minutes. You do not need to code.

**What you will end up with:** a workspace for your blog, an AI connected with your own key, a rulebook learned
from how your blog already writes, and a pipeline that turns a topic into a reviewed draft.

> New here? You can do steps 1 to 4 and 6 with no API key at all. The built-in **Demo AI** writes labelled
> template text so you can see how everything works before you spend anything.

---

## 1. Start the app

You need three things installed: Python 3.10+, Node 18+, and the Graftcode Gateway (`gg`,
[install guide](https://docs.graftcode.com/quick-start)).

In a terminal, from the `graftcode` folder:

```bash
bash scripts/start.sh
```

When it finishes, open **http://localhost:5173**. To stop everything later: `bash scripts/stop.sh`.

If the page says it cannot reach the gateway, the start command is not running. Run it again.

## 2. Look around

The left sidebar has:

| Screen | What it is for |
|---|---|
| **Pipeline** | The flow of steps that turns a topic into a draft. |
| **Content planner** | A calendar: schedule topics and create drafts on a date. |
| **Rulebook** | The rules your blog follows. |
| **Settings & keys** | Your blog details, your AI key, and other keys. |

At the top of the sidebar, the **Workspace** menu switches between blogs or clients. The **+** button creates a
new one.

The pink strip along the bottom shows every call the page makes to the Python side (through Graftcode).

## 3. Try the offline demo

1. Open **Pipeline**.
2. In the toolbar, type a topic, for example `How to read a retention table`.
3. Press **Run pipeline**.

Each box turns orange while it runs and black when it is done. The run **stops at Human review** and a panel
opens with the draft.

4. Read the draft. The **SEO** tab shows a score and exactly what to fix.
5. Press **Approve** (or **Reject**). After approval it finishes the last steps. Nothing is published: the
   **Publish** step is a dry run until you change it.

Click any box to see its **Result**, change its **Settings**, or **Run this step** again.

## 4. Create a workspace for your own blog

1. Press **+** next to the Workspace menu.
2. Name it, enter your blog address, and describe what it is about.
3. Under **Start from**, choose **Live blog** (it has no sample data) and press **Create workspace**.

Everything below happens inside this workspace. Each workspace keeps its own keys, rules, plan and pipelines.

## 5. Connect your AI (add your OpenAI key)

1. Open **Settings & keys**. The first card is **Connect your AI**.
2. Leave the provider on **OpenAI**. (Anthropic, Groq, Moonshot and OpenRouter work the same way.)
3. Paste your OpenAI API key into the box. Use the **Paste** button, or press Cmd+V (Ctrl+V on Windows). The
   eye icon shows or hides what you pasted.
   Do not have a key? Create one at <https://platform.openai.com/api-keys>.
4. Press **Save and use**.

The app saves the key, makes OpenAI the AI for the whole workspace, and sends one tiny request to check that
the key works (it costs a fraction of a cent). You will see either a black confirmation or a red message
explaining what is wrong.

Good to know:

- The key is stored **only on your computer**, and is sent only to OpenAI. After you save it the app shows only
  its last 4 characters, never the whole key.
- You can change AI later: paste another key, or press **Use the demo AI instead**.
- A different AI for one step? Open the step on the Pipeline and pick a provider, model and key there.
- If the model is not available on your account, set another under **Default AI → Model** (for example
  `gpt-4.1`) and press **Save settings**.

If you cannot paste into the browser, run this in a terminal instead (it asks for the key with hidden input):

```bash
bash scripts/add-key.sh YOUR-WORKSPACE-NAME openai --default
```

## 6. Teach it how your blog writes

1. Open **Rulebook**.
2. Press **Learn from my blog**. It reads your published posts (it finds them from your blog address) and
   measures how you write: how posts open, length, whether you use em dashes, FAQ sections and schema, headings
   and more.
3. Read the rules. Each shows the evidence, for example "11 of 14 posts open with a question".
4. Switch off any rule you disagree with, click a rule to reword it, or add your own at the bottom.

From now on every draft is written to these rules and checked against them.

## 7. Add your own instructions

Every AI step has a box called **Your instructions**.

1. On the **Pipeline**, click **Write draft**.
2. In **Your instructions**, write in plain language, for example `Write for busy founders. Use concrete examples.`
3. Open the **Prompt** tab and press **Preview prompt** to see exactly what the AI will be sent. This costs
   nothing.

Blog-wide instructions go in **Settings → Voice**. They are added to every AI prompt.

## 8. Write a real article

1. **Pipeline** → type a topic (and, if you like, a keyword) → **Run pipeline**.
2. When the review panel opens, read the draft. Press **Edit** to change it. If you changed something, press
   **Save and re-check SEO** to see the new score.
3. Press **Approve** or **Reject**. Reject stops everything and records your note.

Tip: the SEO tab's **To fix** list tells you what to change, for example a title that is too long.

## 9. Plan content and schedule it

1. Open **Content planner**. The left side is your **idea library**, filled by the RSS and keyword steps or by
   you (type an idea and press **Add**). The chips filter by category.
2. **Drag an idea onto a day** to schedule it. Click the item to set the time, keyword and notes.
3. Press **Create draft now** on an item, or **Create drafts that are due** to make drafts for everything whose
   time has passed. Drafts wait for your review.

To make it happen automatically on a timer, press **Schedule on GitHub**. It produces a workflow file and the
workspace files (no keys). Commit them to your site repository and add the secrets it lists. A GitHub Action will
then create drafts on schedule and open a **pull request** for you to review. Nothing is published until you merge.

## 10. Reddit and publishing

- **Reddit post ideas** drafts posts for you to post yourself. Pick a kind of post (discussion, contrarian take,
  comparison with a table, comparison with competitors, how-to, feedback), add your **disclosure line**, and read
  the warnings before you post. It never posts anything.
- **Publish** opens a GitHub pull request with the approved article. It is a **dry run** until you set its mode
  to a pull request, and it never merges. Set the repository under **Settings → Publishing and Reddit**.

## 11. Use it from Claude or Cursor (optional)

Everything is also available as tools at `http://localhost:8081/mcp`. Two do the whole job:

- `studio_write_article`: write an article for a topic and get the draft and SEO report.
- `studio_decide`: approve or reject it, after you have read it.

Connect it with the Cursor or Claude Desktop setup in the main README, then just ask: "Write an article on X for
my workspace."

---

## If something goes wrong

| You see | What to do |
|---|---|
| "Cannot reach the Graftcode gateway" | Run `bash scripts/start.sh` again. |
| "No API key for openai" | Settings → Connect your AI → paste your key. |
| The key check shows a red message | Read it: usually the key was copied wrong, has no credit, or the model is not available to your account. |
| A step shows an error | Click it, then open **Result** for the reason in plain words. |
| "Port already in use" | `bash scripts/stop.sh`, then start again. |

## Staying safe

- Nothing is published without your approval, and publishing is a dry run by default.
- Your API keys never leave your computer except to the provider they belong to.
- The app has no login, so keep it on your own computer. Do not expose it to the internet.
- Check every claim in a draft, especially comparisons with competitors, before you post it.

More detail (steps, providers, scheduling, security) is in [STUDIO.md](STUDIO.md).
