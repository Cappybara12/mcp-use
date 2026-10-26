"""Command line runner, used by the scheduled GitHub Action:  graft-studio run-due --workspace NAME --out content/drafts"""
from __future__ import annotations

import argparse
import getpass
import json
import sys

from . import scheduler, store
from .store import StudioError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="graft-studio", description="Run Graft Studio pipelines without the dashboard.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run-due", help="Create drafts for plan items whose date has passed.")
    run.add_argument("--workspace", required=True)
    run.add_argument("--out", default="", help="Folder to write the drafts to (for a pull request).")
    run.add_argument("--max", type=int, default=5, help="Most items to process in one go.")
    lst = sub.add_parser("list-due", help="Show plan items that are due.")
    lst.add_argument("--workspace", required=True)
    key = sub.add_parser("set-key", help="Save an API key for a workspace (asks for it with hidden input).")
    key.add_argument("--workspace", required=True)
    key.add_argument("--provider", required=True, help="openai, anthropic, groq, moonshot, openrouter, tinyfish, dataforseo or github")
    key.add_argument("--name", default="main", help="A name for this key (default: main).")
    key.add_argument("--default", action="store_true", help="Also make this provider and key the workspace default for AI steps.")
    key.add_argument("--stdin", action="store_true", help="Read the key from standard input instead of asking (for scripts).")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "set-key":
            return _set_key(args)
        if args.cmd == "list-due":
            for item in scheduler.due_items(args.workspace):
                print(f"{item['scheduled_for']}  {item['title']}")
            return 0
        results = scheduler.run_due(args.workspace, out_dir=args.out, max_items=args.max)
    except StudioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not results:
        print("Nothing is due.")
    failed = 0
    for r in results:
        mark = "ok " if r["ok"] else "ERR"
        failed += 0 if r["ok"] else 1
        print(f"[{mark}] {r['item']}" + (f"  -> {r['file']}" if r.get("file") else "") + (f"  ({r['error']})" if r.get("error") else ""))
    return 1 if failed else 0


def _set_key(args) -> int:
    """Store a key without it ever appearing on screen, in a shell history, or in a browser."""
    from . import providers

    if args.provider not in providers.KEY_PROVIDERS:
        raise StudioError(f"Unknown provider {args.provider!r}. Choose one of: {', '.join(providers.KEY_PROVIDERS)}.")
    store.ws_dir(args.workspace)                     # fail early if the workspace does not exist
    secret = sys.stdin.read().strip() if args.stdin else getpass.getpass(f"Paste your {args.provider} key (it will not be shown): ").strip()
    store.set_secret(args.workspace, args.name, args.provider, secret)
    if args.default and args.provider in providers.LLM_PROVIDERS:
        store.save_config(args.workspace, {"default_provider": args.provider, "default_model": "", "default_key_slot": args.name})
    saved = next(k for k in store.list_secrets(args.workspace) if k["slot"] == args.name)
    print(f"Saved {args.provider} key '{args.name}' ({saved['masked']}) for workspace '{args.workspace}'."
          + (f" {args.provider} is now this workspace's default AI." if args.default and args.provider in providers.LLM_PROVIDERS else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
