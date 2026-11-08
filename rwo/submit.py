"""rwo submit: validate the reviewer's step.json and turn it into the change guide and proposed code."""
import json, os, re, subprocess, tempfile, datetime
from . import state as st, analyzer
from .queue import current, work_name, WORK
from .progress import emit, task, line, now

PRIORITIES = ["blocking", "fix-before-production", "optional"]
LABEL = {"blocking": "Blocking", "fix-before-production": "Fix before production", "optional": "Optional",
         "no-change-needed": "No change needed"}
NATIONAL_ID = re.compile(r"(?<!\d)\d{3}-\d{7}-\d(?!\d)")
PHONE = re.compile(r"(?<![\w-])\+?1?[\s-]?\(?8[024]9\)?[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
SAFE_ID = "000-0000000-0"


def node_check(code):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(code)
        p = f.name
    try:
        r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
        return r.returncode == 0, (r.stderr.strip().splitlines() or [""])[-1]
    finally:
        os.unlink(p)


def validate(ans, ctx, s, adaptor):
    errs = []
    if ans.get("workflow") != ctx["workflow"]:
        errs.append(f"`workflow` must be exactly \"{ctx['workflow']}\".")
    if ans.get("step") != ctx["step"]:
        errs.append(f"`step` must be exactly \"{ctx['step']}\".")
    for k in ("summary", "proposed_code", "sandbox_tests", "findings", "automatic_findings", "priority"):
        if k not in ans:
            errs.append(f"Missing `{k}`.")
    if errs:
        return errs
    auto_ids = {f["id"]: f for f in ctx["automatic_findings"]}
    answered = {a.get("id"): a for a in ans["automatic_findings"]}
    for aid in auto_ids:
        a = answered.get(aid)
        if not a:
            errs.append(f"Automatic finding {aid} ({auto_ids[aid]['rule']} line {auto_ids[aid]['line']}) is not answered.")
        elif a.get("status") not in ("confirmed", "discarded") or not a.get("reason"):
            errs.append(f"{aid}: status must be confirmed or discarded, with a reason.")
    def ids_of(f):
        v = f.get("from") or []
        return [x.strip() for x in (v.split(",") if isinstance(v, str) else v)]
    from_ids = {i for f in ans["findings"] for i in ids_of(f)}
    for aid, a in answered.items():
        if a.get("status") == "confirmed" and aid not in from_ids:
            errs.append(f"{aid} is confirmed but has no entry in `findings` (\"from\": \"{aid}\").")
    for f in ans["findings"]:
        if f.get("priority") not in PRIORITIES:
            errs.append(f"Finding \"{f.get('title', '?')}\": priority must be one of {PRIORITIES}.")
        for k in ("title", "today", "change"):
            if not f.get(k):
                errs.append(f"Finding \"{f.get('title', '?')}\": missing `{k}`.")
    expected = next((p for p in PRIORITIES if any(f.get("priority") == p for f in ans["findings"])), "no-change-needed")
    if ans["priority"] != expected:
        errs.append(f"`priority` should be \"{expected}\" (the highest priority among the findings).")
    code = ans["proposed_code"]
    if ans["findings"]:
        if "[CHANGE]" not in code:
            errs.append("`proposed_code` has no `// [CHANGE]` mark.")
        ok, msg = node_check(code)
        if not ok:
            errs.append(f"`proposed_code` does not pass node --check: {msg}")
        else:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
                tf.write(code)
            still = {f["rule"]: f for f in analyzer.analyze(tf.name, adaptor)["findings"]}
            os.unlink(tf.name)
            for f in ans["findings"]:
                for fid in ids_of(f):
                    src = auto_ids.get(fid)
                    if src and f.get("fixed_in_code", True) and src["rule"] in still and src["rule"] != "R09":
                        errs.append(f"{fid} ({src['rule']}) is marked as fixed, but the proposed code still "
                                    f"triggers it at line {still[src['rule']]['line']}. Fix it or set \"fixed_in_code\": false.")
    if len(ans["sandbox_tests"]) < 2:
        errs.append("At least 2 sandbox tests are required.")
    text = json.dumps(ans, ensure_ascii=False)
    ids = [m for m in NATIONAL_ID.findall(text) if m != SAFE_ID]
    if ids or PHONE.search(text):
        errs.append("Personal data pattern found (national ID or phone number). Use 000-0000000-0 or <test phone>.")
    for q in ans.get("questions", []):
        if not q.get("owner") or not q.get("text"):
            errs.append("Every question needs `owner` and `text`.")
    return errs


def render_guide(ans, wf, s, state):
    d = datetime.date.today().isoformat()
    out = [f"# {wf['key']} · Change {s['n']} · {s['name']}", "",
           f"**Status:** proposal ({d}). **Code reviewed:** pulled on {state['project'].get('pulled_at', '')}. "
           f"**Credentials point to test environments:** {state.get('env_answer') or 'not confirmed'}.", "",
           "| Item | Value |", "|---|---|", f"| Workflow | {wf['name']} |", f"| Step | {s['name']} |",
           f"| Adaptor | `{s.get('adaptor', '')}` |", "",
           f"**Priority:** {LABEL[ans['priority']]}", "",
           "## What this step does", "", ans["summary"], "", "## What happens today", ""]
    if ans["findings"]:
        for f in ans["findings"]:
            out += [f"- **{f['title']}** ({LABEL[f['priority']]}): {f['today']}"]
    else:
        out += ["No problems found."]
    out += ["", "## How the change works", ""]
    for f in ans["findings"]:
        out += [f"- **{f['title']}:** {f['change']}"]
    if ans.get("behavior"):
        out += ["", "| What happens | Run result | What the log says |", "|---|---|---|"]
        out += [f"| {b['what_happens']} | {b['run_result']} | {b['log']} |" for b in ans["behavior"]]
    out += ["", "## Complete code", "", "```js", ans["proposed_code"].rstrip(), "```", "",
            "## How to test in a sandbox", ""]
    for i, t in enumerate(ans["sandbox_tests"], 1):
        out += [f"**Test {i}. {t['name']}**", "", "Input:", "```json",
                json.dumps(t.get("input", {}), ensure_ascii=False, indent=2), "```",
                f"Expected log: {t.get('expected_log', '')}", ""]
    if ans.get("assumptions") or ans.get("questions"):
        out += ["## Assumptions and questions for the client", ""]
        out += [f"- **Assumption:** {a}" for a in ans.get("assumptions", [])]
        out += [f"- **Question ({q['owner']}):** {q['text']}" for q in ans.get("questions", [])]
    return "\n".join(out) + "\n"


def run(root, path):
    state = st.load(root)
    wf, s = current(state)
    if not s or s["status"] != "in_progress":
        emit("✖ No step is being reviewed. Run `rwo next` first.")
        return 1
    ctx = json.load(open(os.path.join(root, WORK, work_name(wf, s) + ".next.json"), encoding="utf-8"))
    try:
        ans = json.load(open(os.path.join(root, path), encoding="utf-8"))
    except Exception as e:
        emit(f"✖ The answer file is not valid JSON: {e}")
        return 1
    errs = validate(ans, ctx, s, s.get("adaptor", ""))
    if errs:
        print("REJECTED: fix these items in the answer file and run rwo submit again:")
        for e in errs:
            print(f"  - {e}")
        return 1
    wdir = os.path.join(root, st.REVIEW_DIR, wf["dir"])
    os.makedirs(os.path.join(wdir, "proposed"), exist_ok=True)
    guide = os.path.join(wdir, f"{wf['key'].lower()}-step{s['n']}-{s['id']}.md")
    with open(guide, "w", encoding="utf-8") as f:
        f.write(render_guide(ans, wf, s, state))
    with open(os.path.join(wdir, "proposed", s["file"]), "w", encoding="utf-8") as f:
        f.write(ans["proposed_code"].rstrip() + "\n")
    with open(os.path.join(root, WORK, work_name(wf, s) + ".step.json"), "w", encoding="utf-8") as f:
        json.dump(ans, f, ensure_ascii=False, indent=2)
    c = {p: sum(1 for f in ans["findings"] if f["priority"] == p) for p in PRIORITIES}
    s.update(status="done", done_at=now(), counts=c, priority=ans["priority"],
             guide=os.path.relpath(guide, root), titles=[f["title"] for f in ans["findings"]])
    st.save(state, root)
    parts = [f"{n} {LABEL[p].lower()}" for p, n in c.items() if n]
    emit(line(state, f"✔ {wf['key']} · step {s['n']}/{len(wf['steps'])} \"{s['name']}\": "
                     f"{', '.join(parts) or 'no change needed'}"))
    return 0
