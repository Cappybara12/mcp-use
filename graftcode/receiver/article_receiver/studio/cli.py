"""Command line runner, used by the scheduled GitHub Action:  graft-studio run-due --workspace NAME --out content/drafts"""
from __future__ import annotations

import argparse
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
    args = parser.parse_args(argv)
    try:
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


if __name__ == "__main__":
    raise SystemExit(main())
