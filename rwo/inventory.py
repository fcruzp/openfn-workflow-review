"""rwo inventory: read the pulled workflows and build the work queue."""
import os, glob, datetime, yaml
from collections import deque
from . import state as st, pull
from .progress import emit, task


def load_workflow(d):
    ymls = [f for f in glob.glob(os.path.join(d, "*.y*ml"))]
    if not ymls:
        return None
    with open(ymls[0], encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    wf["_yaml"] = os.path.basename(ymls[0])
    return wf


def ordered_steps(wf):
    """Steps in real order: breadth-first from the trigger, following the edges."""
    steps = wf.get("steps", [])
    by_id = {s["id"]: s for s in steps}
    triggers = [s for s in steps if s.get("type") in ("cron", "webhook", "kafka")]
    start = [t["id"] for t in triggers] or ([wf.get("start")] if wf.get("start") in by_id else [])
    seen, order, q = set(), [], deque(start)
    while q:
        sid = q.popleft()
        if sid in seen or sid not in by_id:
            continue
        seen.add(sid)
        s = by_id[sid]
        if s.get("expression"):
            order.append(s)
        for nxt in (s.get("next") or {}):
            q.append(nxt)
    order += [s for s in steps if s.get("expression") and s["id"] not in seen]  # unreachable steps last
    return triggers, order


def describe_trigger(t):
    if t.get("type") == "cron":
        return f"cron `{t.get('cron_expression')}` (UTC)"
    return t.get("type", "unknown")


def edge_text(s, by_id):
    out = []
    for nxt, e in (s.get("next") or {}).items():
        e = e or {}
        label = f" · label \"{e['label']}\"" if e.get("label") else ""
        dis = " · **disabled**" if e.get("disabled") else ""
        out.append(f"{by_id.get(nxt, {}).get('name', nxt)} ({e.get('condition', 'always')}{label}{dis})")
    return "; ".join(out) or "end"


def run(root=".", only=None):
    dirs = pull.workflow_dirs(root)
    if not dirs:
        emit("✖ No workflows found. Run `rwo pull` first.")
        return 1
    prev = st.load(root) or {}
    prev_steps = {(w["dir"], s["file"]): s for w in prev.get("workflows", []) for s in w["steps"]}
    new_hashes = pull.hashes(root)
    old_hashes = prev.get("hashes", {})
    proj = yaml.safe_load(open(os.path.join(root, "openfn.yaml"), encoding="utf-8")).get("project", {}) \
        if os.path.exists(os.path.join(root, "openfn.yaml")) else {}

    workflows, md = [], []
    for i, d in enumerate(dirs, 1):
        wf = load_workflow(d)
        if not wf:
            continue
        triggers, steps = ordered_steps(wf)
        by_id = {s["id"]: s for s in wf.get("steps", [])}
        key, dname = f"WF{i}", os.path.basename(d)
        in_scope = only is None or wf.get("name") == only
        entry = {"key": key, "id": wf.get("id"), "name": wf.get("name"), "dir": dname,
                 "yaml": wf["_yaml"], "triggers": [describe_trigger(t) for t in triggers],
                 "in_scope": in_scope, "status": "pending", "steps": []}
        md += [f"## {key} · {wf.get('name')}", "",
               f"- **Trigger:** {', '.join(entry['triggers']) or 'none'}",
               f"- **Steps:** {len(steps)}", "",
               "| # | Step | Adaptor | Credential | Next |", "|---|---|---|---|---|"]
        for n, s in enumerate(steps, 1):
            f = os.path.basename(s["expression"])
            h = new_hashes.get(dname, {}).get(f)
            old = prev_steps.get((dname, f))
            unchanged = old and old_hashes.get(dname, {}).get(f) == h
            cred = s.get("configuration") or s.get("credential") or s.get("project_credential") or ""
            step = {"n": n, "id": s["id"], "name": s.get("name", s["id"]), "file": f, "hash": h,
                    "adaptor": s.get("adaptor", ""), "credential": cred if isinstance(cred, str) else str(cred),
                    "next": edge_text(s, by_id), "in_scope": in_scope,
                    "status": old["status"] if unchanged else "pending"}
            if unchanged:
                for k in ("counts", "started_at", "done_at"):
                    if k in old:
                        step[k] = old[k]
            entry["steps"].append(step)
            md.append(f"| {n} | {step['name']} | `{step['adaptor']}` | {step['credential'] or '—'} | {step['next']} |")
        md.append("")
        workflows.append(entry)

    state = {**prev, "workflows": workflows, "hashes": new_hashes,
             "project": {"name": proj.get("name") or proj.get("id", ""), "endpoint": proj.get("endpoint", ""),
                         "uuid": proj.get("uuid", ""),
                         "pulled_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")},
             "mode": prev.get("mode", "full")}
    state.pop("pending_changes", None)
    st.save(state, root)
    total = sum(len(w["steps"]) for w in workflows if w["in_scope"])
    with open(os.path.join(root, st.REVIEW_DIR, "inventory.md"), "w", encoding="utf-8") as f:
        f.write(f"# Inventory: {state['project']['name']}\n\n" + "\n".join(md))
    creds = sorted({s["credential"] for w in workflows for s in w["steps"] if s["credential"]})
    emit(f"✔ Inventory: {len(workflows)} workflows, {sum(len(w['steps']) for w in workflows)} steps"
         f" ({total} in scope) · saved in review/inventory.md")
    for w in workflows:
        if w["in_scope"]:
            task("create", f"{w['key']} · {w['name']} · {len(w['steps'])} steps", "pending")
    task("create", "Questions for the client", "pending")
    task("create", "Final summary", "pending")
    print("CREDENTIALS " + (", ".join(creds) if creds else "(none listed in the workflow files)"))
    return 0
