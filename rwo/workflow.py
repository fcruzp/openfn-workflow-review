"""rwo close-workflow: complete the proposed workflow folder and its CHANGES.md."""
import os, shutil
from . import state as st
from .progress import emit, task

LABEL = {"blocking": "Blocking", "fix-before-production": "Fix before production", "optional": "Optional",
         "no-change-needed": "No change needed"}


def find(state, key):
    return next((w for w in state["workflows"] if w["key"] == key.upper()), None)


def close(root, key):
    state = st.load(root)
    wf = find(state, key)
    if not wf:
        emit(f"✖ Unknown workflow {key}.")
        return 1
    pending = [s["name"] for s in wf["steps"] if s["status"] != "done"]
    if pending:
        emit(f"✖ {wf['key']} still has steps to review: {', '.join(pending)}.")
        return 1
    src = os.path.join(root, "workflows", wf["dir"])
    dst = os.path.join(root, st.REVIEW_DIR, wf["dir"], "proposed")
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(os.path.join(src, wf["yaml"]), os.path.join(dst, wf["yaml"]))
    for s in wf["steps"]:
        if not os.path.exists(os.path.join(dst, s["file"])):
            shutil.copy2(os.path.join(src, s["file"]), os.path.join(dst, s["file"]))
    rows = ["# Proposed changes: " + wf["name"], "",
            "Test this folder in a Lightning sandbox before applying anything to the real project.", "",
            "| # | Step | Priority | Change | Guide |", "|---|---|---|---|---|"]
    for s in wf["steps"]:
        guide = os.path.basename(s.get("guide", ""))
        rows.append(f"| {s['n']} | {s['name']} | {LABEL.get(s.get('priority', ''), '')} | "
                    f"{'; '.join(s.get('titles', [])) or 'No change'} | [{guide}](../{guide}) |")
    with open(os.path.join(dst, "CHANGES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    wf["proposed"] = True
    maybe_done(state, wf)
    st.save(state, root)
    emit(f"✔ {wf['key']}: complete proposed workflow ready in review/{wf['dir']}/proposed/ (with CHANGES.md).")
    return 0


def maybe_done(state, wf):
    if wf.get("proposed") and wf.get("diagram") and wf.get("tests") and wf.get("status") != "done":
        wf["status"] = "done"
        task("update", f"{wf['key']} · {wf['name']} · {len(wf['steps'])} steps", "completed")
