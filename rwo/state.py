"""Single source of truth for the review: review/state.json."""
import json, os, hashlib

REVIEW_DIR = "review"
STATE_FILE = os.path.join(REVIEW_DIR, "state.json")


def load(root="."):
    p = os.path.join(root, STATE_FILE)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(state, root="."):
    os.makedirs(os.path.join(root, REVIEW_DIR), exist_ok=True)
    p = os.path.join(root, STATE_FILE)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    write_progress_md(state, root)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def finished(state):
    return all(st["status"] == "done"
               for wf in state.get("workflows", []) for st in wf["steps"] if st.get("in_scope", True))


def write_progress_md(state, root="."):
    """Human-readable view of state.json (never edited by hand)."""
    p = state.get("project", {})
    out = [f"# Review progress: {p.get('name', '')}", "",
           f"- **Endpoint:** {p.get('endpoint', '')}",
           f"- **Pulled:** {p.get('pulled_at', '')}",
           f"- **Credentials point to test environments:** {state.get('env_answer') or 'not answered yet'}",
           f"- **Mode:** {state.get('mode', 'full')}", "",
           "| Workflow | Step | Status | Blocking | Fix before production | Optional |",
           "|---|---|---|---|---|---|"]
    for wf in state.get("workflows", []):
        for st in wf["steps"]:
            c = st.get("counts", {})
            status = st["status"] if st.get("in_scope", True) else "out of scope"
            out.append(f"| {wf['key']} · {wf['name']} | {st['name']} | {status} | "
                       f"{c.get('blocking', '')} | {c.get('fix-before-production', '')} | {c.get('optional', '')} |")
    with open(os.path.join(root, REVIEW_DIR, "progress.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
