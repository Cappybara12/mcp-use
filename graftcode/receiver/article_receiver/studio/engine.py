"""Running a pipeline: graph order, per-node execution, the review pause, and plan-item bookkeeping."""
from __future__ import annotations

from . import nodes, store
from .net import NetError
from .nodes import AwaitReview, Ctx, NODE_TYPES
from .store import StudioError, now_iso

MAX_OUTPUT_CHARS = 60_000


# ── graph helpers ─────────────────────────────────────────────────────────────

def topo_order(pipeline: dict) -> list[str]:
    ids = [n["id"] for n in pipeline["nodes"]]
    indeg = {i: 0 for i in ids}
    out: dict[str, list[str]] = {i: [] for i in ids}
    for e in pipeline["edges"]:
        indeg[e["target"]] += 1
        out[e["source"]].append(e["target"])
    ready = [i for i in ids if indeg[i] == 0]
    order = []
    while ready:
        ready.sort(key=ids.index)          # stable: ties follow the order nodes were added
        n = ready.pop(0)
        order.append(n)
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
    return order


def ancestors(pipeline: dict, node_id: str) -> list[str]:
    parents: dict[str, list[str]] = {n["id"]: [] for n in pipeline["nodes"]}
    for e in pipeline["edges"]:
        parents[e["target"]].append(e["source"])
    seen, stack = set(), [node_id]
    while stack:
        cur = stack.pop()
        for p in parents.get(cur, []):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return [i for i in topo_order(pipeline) if i in seen]


def descendants(pipeline: dict, node_id: str) -> list[str]:
    return [i for i in topo_order(pipeline) if node_id in ancestors(pipeline, i)]


def _node(pipeline: dict, node_id: str) -> dict:
    for n in pipeline["nodes"]:
        if n["id"] == node_id:
            return n
    raise StudioError(f"Node '{node_id}' is not in this pipeline.")


def _shrink(value):
    if isinstance(value, str):
        return value if len(value) <= MAX_OUTPUT_CHARS else value[:MAX_OUTPUT_CHARS] + "\n...[truncated]"
    if isinstance(value, list):
        return [_shrink(v) for v in value[:500]]
    if isinstance(value, dict):
        return {k: _shrink(v) for k, v in value.items()}
    return value


# ── runs ──────────────────────────────────────────────────────────────────────

def _blank_state() -> dict:
    return {"status": "pending", "output": None, "error": "", "logs": [], "started_at": "", "finished_at": ""}


def _plan_update(ws: str, run: dict, status: str) -> None:
    item_id = (run.get("item") or {}).get("id")
    if item_id:
        store.set_plan_fields(ws, item_id, status=status, run_id=run["id"])


def _sync(ws: str, run: dict, pipeline: dict) -> dict:
    """Make sure every node has a state entry and compute the overall run status."""
    for n in pipeline["nodes"]:
        run["nodes"].setdefault(n["id"], _blank_state())
    states = {i: run["nodes"][i]["status"] for i in run["nodes"] if i in {n["id"] for n in pipeline["nodes"]}}
    if "error" in states.values():
        run["status"] = "error"
    elif "awaiting_review" in states.values():
        run["status"] = "awaiting_review"
    elif states and all(s == "done" for s in states.values()):
        run["status"] = "done"
    elif "running" in states.values():
        run["status"] = "running"
    else:
        run["status"] = "ready"
    run["order"] = topo_order(pipeline)
    return run


def start_run(ws: str, pipeline_id: str, item: dict | None = None) -> dict:
    pipeline = store.get_pipeline(ws, pipeline_id)
    item = item or {}
    clean_item = {k: str(item.get(k, ""))[:2000] for k in ("id", "title", "keyword", "category", "notes") if item.get(k)}
    run = {"id": store.new_run_id(), "pipeline_id": pipeline_id, "title": clean_item.get("title", ""),
           "item": clean_item, "status": "ready", "nodes": {}, "created_at": now_iso()}
    _sync(ws, run, pipeline)
    store.save_run(ws, run)
    _plan_update(ws, run, "drafting")
    return run


def get_run(ws: str, run_id: str) -> dict:
    run = store.load_run(ws, run_id)
    pipeline = store.get_pipeline(ws, run["pipeline_id"])
    return _sync(ws, run, pipeline)


def _upstream(run: dict, pipeline: dict, node_id: str) -> dict:
    merged: dict = {}
    for aid in ancestors(pipeline, node_id):
        state = run["nodes"].get(aid) or _blank_state()
        if state["status"] != "done":
            label = NODE_TYPES[_node(pipeline, aid)["type"]]["label"]
            if state["status"] == "awaiting_review":
                raise StudioError(f"A person has to approve or reject the draft in '{label}' first.")
            raise StudioError(f"Run the step before this one first: {label}.")
        merged.update(state["output"] or {})
    return merged


def run_node(ws: str, run_id: str, node_id: str) -> dict:
    """Run a single node (re-reading its current config). Returns the whole run so the UI can refresh."""
    run = store.load_run(ws, run_id)
    pipeline = store.get_pipeline(ws, run["pipeline_id"])
    node = _node(pipeline, node_id)
    _sync(ws, run, pipeline)
    state = run["nodes"][node_id]
    ctx = Ctx(ws, run)
    state.update(status="running", error="", started_at=now_iso(), finished_at="", logs=[])
    store.save_run(ws, run)
    if node.get("config", {}).get("enabled", True) is False:
        state.update(status="done", output={}, logs=["Skipped: this step is disabled."], finished_at=now_iso())
        _sync(ws, run, pipeline)
        store.save_run(ws, run)
        return run
    try:
        up = _upstream(run, pipeline, node_id)
        output = NODE_TYPES[node["type"]]["run"](ctx, node.get("config", {}), up)
        state.update(status="done", output=_shrink(output))
    except AwaitReview:
        state.update(status="awaiting_review", output=None)
        _plan_update(ws, run, "review")
    except (StudioError, NetError) as exc:
        state.update(status="error", error=str(exc)[:600], output=None)
    except Exception as exc:  # a bug in a node must not crash the gateway or leak details
        state.update(status="error", error=f"Unexpected error in this step ({exc.__class__.__name__}).", output=None)
    state["logs"] = ctx.logs
    state["finished_at"] = now_iso()
    # Anything after a re-run node is stale.
    for d in descendants(pipeline, node_id):
        if run["nodes"][d]["status"] in ("done", "error", "awaiting_review") and state["status"] != "done":
            run["nodes"][d] = _blank_state()
    if node["type"] == "publish" and state["status"] == "done":
        _plan_update(ws, run, "published")
    _sync(ws, run, pipeline)
    store.save_run(ws, run)
    return run


def run_until_blocked(ws: str, run_id: str) -> dict:
    """Run every pending node in order; stops at the review step or the first error."""
    run = get_run(ws, run_id)
    pipeline = store.get_pipeline(ws, run["pipeline_id"])
    for nid in topo_order(pipeline):
        if run["nodes"][nid]["status"] != "pending":
            continue
        run = run_node(ws, run_id, nid)
        if run["nodes"][nid]["status"] in ("error", "awaiting_review"):
            break
    return get_run(ws, run_id)


def reset_from(ws: str, run_id: str, node_id: str) -> dict:
    run = store.load_run(ws, run_id)
    pipeline = store.get_pipeline(ws, run["pipeline_id"])
    for nid in [node_id, *descendants(pipeline, node_id)]:
        run["nodes"][nid] = _blank_state()
    _sync(ws, run, pipeline)
    store.save_run(ws, run)
    return run


def review(ws: str, run_id: str, node_id: str, decision: str, notes: str = "", markdown: str = "") -> dict:
    run = store.load_run(ws, run_id)
    pipeline = store.get_pipeline(ws, run["pipeline_id"])
    node = _node(pipeline, node_id)
    if node["type"] != "review":
        raise StudioError("That node is not a review step.")
    state = run["nodes"].get(node_id) or _blank_state()
    if state["status"] != "awaiting_review":
        raise StudioError("This review is not waiting for a decision. Run the steps before it first.")
    if decision not in ("approve", "reject"):
        raise StudioError("Decision must be 'approve' or 'reject'.")
    final = (markdown or "").strip()
    if len(final) > 400_000:
        raise StudioError("The edited draft is too large.")
    if decision == "approve":
        if final:
            store.save_draft(ws, run_id, final + "\n")
        state.update(status="done", output={"review": {"approved": True, "notes": notes[:2000], "final_markdown": final or None,
                                                       "decided_at": now_iso()}}, error="", finished_at=now_iso())
        _plan_update(ws, run, "approved")
    else:
        state.update(status="error", output=None, error="Rejected in review: " + (notes[:300] or "no reason given"), finished_at=now_iso())
        _plan_update(ws, run, "rejected")
    run["nodes"][node_id] = state
    _sync(ws, run, pipeline)
    store.save_run(ws, run)
    return run


def preview_prompt(ws: str, pipeline_id: str, node_id: str, run_id: str = "") -> dict:
    """What the AI would be sent for this node, built from the latest outputs of the run (no AI call)."""
    pipeline = store.get_pipeline(ws, pipeline_id)
    node = _node(pipeline, node_id)
    if node["type"] not in ("outline", "write", "reddit"):
        raise StudioError("Only AI steps (Outline, Write draft, Reddit) have a prompt.")
    run = store.load_run(ws, run_id) if run_id else {"id": "preview", "pipeline_id": pipeline_id, "nodes": {}, "item": {}}
    ctx = Ctx(ws, run)
    up: dict = {}
    for aid in ancestors(pipeline, node_id):
        state = (run.get("nodes") or {}).get(aid)
        if state and state["status"] == "done":
            up.update(state["output"] or {})
    system, user, _task = nodes.build_prompt(ctx, node["type"], node.get("config", {}), up)
    provider, model, slot = ctx.llm_settings(node.get("config", {}))
    return {"system": system, "user": user, "provider": provider, "model": model, "key_slot": slot,
            "missing_inputs": [] if up else ["No earlier step has run yet, so the prompt shows only the rules and your instructions."]}
