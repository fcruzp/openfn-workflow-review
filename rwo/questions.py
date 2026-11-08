"""rwo questions: collect every question from the submitted steps into review/questions.md."""
import os, json, glob
from collections import OrderedDict
from . import state as st
from .progress import emit, task


def run(root):
    state = st.load(root)
    names = {f"{w['key']}-{s['n']:02d}-{s['id']}": (w, s) for w in state["workflows"] for s in w["steps"]}
    groups = OrderedDict()
    for p in sorted(glob.glob(os.path.join(root, st.REVIEW_DIR, "work", "*.step.json"))):
        key = os.path.basename(p)[:-len(".step.json")]
        w, s = names.get(key, (None, None))
        if not w:
            continue
        ans = json.load(open(p, encoding="utf-8"))
        for q in ans.get("questions", []):
            groups.setdefault(q["owner"].strip(), []).append((w, s, q["text"].strip()))
    out = [f"# Questions for the client: {state['project'].get('name', '')}", ""]
    n = 0
    for owner, qs in groups.items():
        out += [f"## {owner}", ""]
        for w, s, text in qs:
            n += 1
            out.append(f"{n}. **{w['key']} · {w['name']} · {s['name']}:** {text}")
        out.append("")
    if n == 0:
        out.append("No open questions.")
    with open(os.path.join(root, st.REVIEW_DIR, "questions.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    task("update", "Questions for the client", "completed")
    emit(f"✔ Questions for the client: {n} questions, grouped by owner · review/questions.md")
    return 0
