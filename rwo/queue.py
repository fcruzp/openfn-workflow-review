"""rwo next: give the model the next step to review, with context and automatic findings."""
import os, json
from . import state as st, analyzer, facts
from .progress import emit, task, now

WORK = os.path.join(st.REVIEW_DIR, "work")


def current(state):
    """The step being reviewed now, or the next pending one (in workflow order)."""
    for wf in state["workflows"]:
        if not wf.get("in_scope", True):
            continue
        for s in wf["steps"]:
            if s["status"] == "in_progress":
                return wf, s
    for wf in state["workflows"]:
        if not wf.get("in_scope", True):
            continue
        for s in wf["steps"]:
            if s["status"] == "pending":
                return wf, s
    return None, None


def work_name(wf, s):
    return f"{wf['key']}-{s['n']:02d}-{s['id']}"


def run(root="."):
    state = st.load(root)
    if not state or not state.get("workflows"):
        emit("✖ No inventory yet. Run `rwo inventory` first.")
        return 1
    wf, s = current(state)
    if wf is None:
        for w in state["workflows"]:
            if not w.get("in_scope", True) or w.get("status") == "done":
                continue
            for flag, cmd in (("proposed", f"rwo close-workflow {w['key']}"),
                              ("diagram", f"rwo diagram {w['key']} <lanes.json>"),
                              ("tests", f"rwo tests {w['key']} <scenarios.json>")):
                if not w.get(flag):
                    print(f"WORKFLOW_NEXT {w['key']} -> run: {cmd}")
                    return 0
        print("ALL_WORKFLOWS_DONE -> run: rwo questions, then rwo summary")
        return 0
    if all(x["status"] == "pending" for x in wf["steps"]):
        task("update", f"{wf['key']} · {wf['name']} · {len(wf['steps'])} steps", "in progress")
    if s["status"] != "in_progress":
        s["status"], s["started_at"] = "in_progress", now()
        st.save(state, root)

    path = os.path.join(root, "workflows", wf["dir"], s["file"])
    code = open(path, encoding="utf-8").read()
    auto = analyzer.analyze(path, s.get("adaptor", ""))
    for i, f in enumerate(auto["findings"], 1):
        f["id"] = f"A{i}"
    steps = wf["steps"]
    i = steps.index(s)
    ctx = {
        "workflow": wf["name"], "workflow_key": wf["key"], "step": s["name"], "step_number": s["n"],
        "steps_in_workflow": len(steps), "file": f"workflows/{wf['dir']}/{s['file']}",
        "adaptor": s.get("adaptor", ""), "credential": s.get("credential", ""),
        "trigger": wf.get("triggers", []), "next_edges": s.get("next", ""),
        "previous_step": steps[i - 1]["name"] if i else None,
        "following_step": steps[i + 1]["name"] if i + 1 < len(steps) else None,
        "environment_is_test": state.get("env_answer"),
        "verified_facts": facts.for_adaptor(s.get("adaptor", "")), "facts_verified_for": facts.VERIFIED_FOR,
        "code_with_line_numbers": "\n".join(f"{n:4d}  {l}" for n, l in enumerate(code.splitlines(), 1)),
        "parse_error": auto["parse_error"], "automatic_findings": auto["findings"],
        "write_your_answer_to": os.path.join(WORK, work_name(wf, s) + ".step.json"),
        "answer_schema": "rwo/schemas/step.schema.md",
    }
    os.makedirs(os.path.join(root, WORK), exist_ok=True)
    out = os.path.join(root, WORK, work_name(wf, s) + ".next.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)
    task("update", f"{wf['key']} · {wf['name']} · {len(steps)} steps", f"step {s['n']}/{len(steps)}: {s['name']}")
    emit(f"▶ {wf['key']} · step {s['n']}/{len(steps)} \"{s['name']}\" · reviewing… "
         f"({len(auto['findings'])} automatic findings to check)")
    print(f"NEXT_FILE {os.path.relpath(out, root)}")
    print(f"ANSWER_FILE {ctx['write_your_answer_to']}")
    return 0
