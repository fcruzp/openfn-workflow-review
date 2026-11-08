"""rwo summary: build review/SUMMARY.md and review/SUMMARY.html from the recorded data (nothing invented)."""
import os, json, glob, html
from . import state as st
from .progress import emit, task

LEVELS = [("blocking", "Blocking"), ("fix-before-production", "Fix before production"), ("optional", "Optional")]
LABEL = dict(LEVELS, **{"no-change-needed": "No change needed", "pending": "Not reviewed yet"})


def collect(root, state):
    work = os.path.join(root, st.REVIEW_DIR, "work")
    answers = {}
    for p in glob.glob(os.path.join(work, "*.step.json")):
        answers[os.path.basename(p)[:-len(".step.json")]] = json.load(open(p, encoding="utf-8"))
    data = {"workflows": [], "blocking": [], "assumptions": [], "institutions": set(), "seconds": 0,
            "totals": {k: 0 for k, _ in LEVELS}, "steps": 0, "pending": 0}
    for wf in state["workflows"]:
        if not wf.get("in_scope", True):
            continue
        w = {"key": wf["key"], "name": wf["name"], "dir": wf["dir"], "triggers": wf.get("triggers", []),
             "counts": {k: 0 for k, _ in LEVELS}, "steps": [], "diagram": wf.get("diagram"),
             "proposed": wf.get("proposed"), "tests": wf.get("tests")}
        for s in wf["steps"]:
            if not s.get("in_scope", True):
                continue
            data["steps"] += 1
            done = s.get("status") == "done"
            data["pending"] += not done
            if done and s.get("started_at") and s.get("done_at"):
                data["seconds"] += s["done_at"] - s["started_at"]
            for k, _ in LEVELS:
                n = (s.get("counts") or {}).get(k, 0)
                w["counts"][k] += n
                data["totals"][k] += n
            guide = os.path.relpath(s["guide"], st.REVIEW_DIR).replace(os.sep, "/") if s.get("guide") else None
            w["steps"].append({"n": s["n"], "name": s["name"], "priority": s.get("priority") if done else "pending",
                               "counts": s.get("counts") or {}, "guide": guide})
            ans = answers.get(f"{wf['key']}-{s['n']:02d}-{s['id']}", {})
            for f in ans.get("findings", []):
                if f.get("priority") == "blocking":
                    data["blocking"].append({"wf": wf["key"], "step": s["name"], "title": f.get("title", ""),
                                             "today": f.get("today", ""), "guide": guide})
            for a in ans.get("assumptions", []):
                data["assumptions"].append((wf["key"], s["name"], a))
        data["institutions"] |= set(wf.get("institutions") or [])
        data["workflows"].append(w)
    data["institutions"] = sorted(data["institutions"])
    return data


def write_md(root, state, d):
    p = state.get("project", {})
    mins = max(1, round(d["seconds"] / 60)) if d["seconds"] else 0
    env = {"yes": "test environments", "no": "production (be careful)"}.get(state.get("env_answer"),
                                                                          state.get("env_answer") or "not answered")
    out = [f"# Review summary: {p.get('name', '')}", "",
           f"- **Project:** {p.get('name', '')} ({p.get('endpoint', '')})",
           f"- **Downloaded:** {p.get('pulled_at', '')}",
           f"- **Credentials point to:** {env}",
           f"- **Review time:** about {mins} min",
           f"- **Workflows / steps:** {len(d['workflows'])} / {d['steps']}"
           + (f" ({d['pending']} not reviewed yet)" if d["pending"] else ""), "",
           "## Issues by workflow", "",
           "| Workflow | Steps | Blocking | Fix before production | Optional |", "|---|---|---|---|---|"]
    for w in d["workflows"]:
        c = w["counts"]
        out.append(f"| {w['key']} · {w['name']} | {len(w['steps'])} | {c['blocking']} | "
                   f"{c['fix-before-production']} | {c['optional']} |")
    t = d["totals"]
    out += [f"| **Total** | **{d['steps']}** | **{t['blocking']}** | **{t['fix-before-production']}** | "
            f"**{t['optional']}** |", "", "## Blocking items", ""]
    out += [f"- **{b['wf']} · {b['step']}:** {b['title']}. {b['today']}" + (f" ([guide]({b['guide']}))" if b["guide"] else "")
            for b in d["blocking"]] or ["None."]
    out += ["", "## Assumptions that could not be verified", ""]
    out += [f"- **{k} · {s}:** {a}" for k, s, a in d["assumptions"]] or ["None."]
    out += ["", "## Partner institutions found in the code (correct them if needed)", ""]
    out += [f"- {i}" for i in d["institutions"]] or ["None recorded."]
    if state.get("pending_changes"):
        out += ["", "## Changes since the previous review", ""] + [f"- {c}" for c in state["pending_changes"]]
    out += ["", "## Where everything is", "",
            "- Change guides: `review/<workflow>/` (one per step)",
            "- Proposed code: `review/<workflow>/proposed/` (`workflow.yaml`, one `.js` per step, `CHANGES.md`)",
            "- Diagrams: `review/<workflow>/diagram/` (`.bpmn` for Lucidchart, `.png` preview)",
            "- Test scenarios and institution guides: `review/tests/test-scenarios.xlsx`",
            "- Questions for the client: `review/questions.md`", "",
            "## What to do next", ""] + [f"{i}. {x}" for i, x in enumerate(NEXT, 1)]
    path = os.path.join(root, st.REVIEW_DIR, "SUMMARY.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return path


NEXT = ["Read the change guides of the blocking items.",
        "Test the proposed code in a Lightning sandbox (never in production), with invented data.",
        "Import each .bpmn into Lucidchart (File → Import → BPMN) and check it against the .png.",
        "Upload test-scenarios.xlsx to Google Drive and choose File → Save as Google Sheets.",
        "Send review/questions.md to the client."]

CSS = """
:root{--bg:#f7f8fa;--card:#fff;--fg:#1d2330;--muted:#5d6678;--line:#e3e6ec;
--block:#c62828;--block-bg:#fde8e8;--fix:#b26a00;--fix-bg:#fff1d6;--opt:#56657a;--opt-bg:#e8edf3;--ok:#2e7d32;--ok-bg:#e3f4e4;--pend:#6b7280;--pend-bg:#eef0f3}
@media (prefers-color-scheme:dark){:root{--bg:#14171d;--card:#1d222b;--fg:#e8ebf0;--muted:#a3abba;--line:#2d3440;
--block:#ff8a80;--block-bg:#3b1f22;--fix:#ffc266;--fix-bg:#3a2e17;--opt:#b4c0d0;--opt-bg:#283141;--ok:#81c784;--ok-bg:#1d3221;--pend:#a3abba;--pend-bg:#2a2f38}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px 48px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:28px 0 10px}
.meta{color:var(--muted);font-size:14px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}.kpi b{display:block;font-size:26px}
.kpi span{color:var(--muted);font-size:13px}.kpi.block b{color:var(--block)}.kpi.fix b{color:var(--fix)}.kpi.opt b{color:var(--opt)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:12px}
.card h3{margin:0 0 6px;font-size:16px}.mix{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--ok-bg);margin:8px 0 12px}
.mix i{display:block}.mix .b{background:var(--block)}.mix .f{background:var(--fix)}.mix .o{background:var(--opt)}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:6px 4px;border-top:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600;white-space:nowrap}
.blocking{color:var(--block);background:var(--block-bg)}.fix-before-production{color:var(--fix);background:var(--fix-bg)}
.optional{color:var(--opt);background:var(--opt-bg)}.no-change-needed{color:var(--ok);background:var(--ok-bg)}.pending{color:var(--pend);background:var(--pend-bg)}
.alert{border-left:4px solid var(--block);background:var(--block-bg);border-radius:8px;padding:10px 14px}.alert li{margin:6px 0}
a{color:inherit}ul.check{list-style:none;padding:0}ul.check li:before{content:"☐ ";color:var(--muted)}
.wrap{overflow-x:auto}
"""


def write_html(root, state, d):
    e = html.escape
    p = state.get("project", {})
    t = d["totals"]
    mins = max(1, round(d["seconds"] / 60)) if d["seconds"] else 0
    h = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>Review summary: {e(p.get('name', ''))}</title><style>{CSS}</style></head><body><main>",
         f"<h1>Review summary: {e(p.get('name', ''))}</h1>",
         f"<div class='meta'>{e(p.get('endpoint', ''))} · downloaded {e(p.get('pulled_at', ''))} · review time about {mins} min"
         + (f" · <b>{d['pending']} steps not reviewed yet</b>" if d["pending"] else "") + "</div>",
         "<div class='kpis'>",
         f"<div class='kpi'><b>{len(d['workflows'])}</b><span>Workflows</span></div>",
         f"<div class='kpi'><b>{d['steps']}</b><span>Steps</span></div>",
         f"<div class='kpi block'><b>{t['blocking']}</b><span>Blocking</span></div>",
         f"<div class='kpi fix'><b>{t['fix-before-production']}</b><span>Fix before production</span></div>",
         f"<div class='kpi opt'><b>{t['optional']}</b><span>Optional</span></div></div>",
         "<h2>Blocking items</h2>"]
    if d["blocking"]:
        h.append("<div class='alert'><ul>")
        for b in d["blocking"]:
            link = f" <a href='{e(b['guide'])}'>Change guide</a>" if b["guide"] else ""
            h.append(f"<li><b>{e(b['wf'])} · {e(b['step'])}:</b> {e(b['title'])}. {e(b['today'])}{link}</li>")
        h.append("</ul></div>")
    else:
        h.append("<p>None.</p>")
    h.append("<h2>Workflows</h2>")
    for w in d["workflows"]:
        c = w["counts"]
        tot = sum(c.values()) or 1
        h.append(f"<div class='card'><h3>{e(w['key'])} · {e(w['name'])}</h3>"
                 f"<div class='meta'>{e(', '.join(w['triggers']))} · {len(w['steps'])} steps · "
                 f"{c['blocking']} blocking, {c['fix-before-production']} fix before production, {c['optional']} optional</div>"
                 f"<div class='mix' role='img' aria-label='priority mix'>"
                 f"<i class='b' style='width:{100 * c['blocking'] / tot:.1f}%'></i>"
                 f"<i class='f' style='width:{100 * c['fix-before-production'] / tot:.1f}%'></i>"
                 f"<i class='o' style='width:{100 * c['optional'] / tot:.1f}%'></i></div>"
                 "<div class='wrap'><table><tr><th>#</th><th>Step</th><th>Priority</th><th>Issues</th><th>Guide</th></tr>")
        for s in w["steps"]:
            pr = s["priority"] or "pending"
            n = sum((s["counts"] or {}).values())
            g = f"<a href='{e(s['guide'])}'>Open</a>" if s["guide"] else ""
            h.append(f"<tr><td>{s['n']}</td><td>{e(s['name'])}</td><td><span class='badge {e(pr)}'>{e(LABEL.get(pr, pr))}</span></td>"
                     f"<td>{n}</td><td>{g}</td></tr>")
        h.append("</table></div></div>")
    h.append("<h2>Assumptions that could not be verified</h2>")
    h.append("<ul>" + "".join(f"<li><b>{e(k)} · {e(s)}:</b> {e(a)}</li>" for k, s, a in d["assumptions"]) + "</ul>"
             if d["assumptions"] else "<p>None.</p>")
    h.append("<h2>Partner institutions found in the code</h2><p>"
             + (e(", ".join(d["institutions"])) or "None recorded.") + " <span class='meta'>(correct them if needed)</span></p>")
    if state.get("pending_changes"):
        h.append("<h2>Changes since the previous review</h2><ul>"
                 + "".join(f"<li>{e(c)}</li>" for c in state["pending_changes"]) + "</ul>")
    h.append("<h2>What to do next</h2><ul class='check'>" + "".join(f"<li>{e(x)}</li>" for x in NEXT) + "</ul>")
    h.append("</main></body></html>")
    path = os.path.join(root, st.REVIEW_DIR, "SUMMARY.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(h))
    return path


def run(root):
    state = st.load(root)
    if not state or not state.get("workflows"):
        emit("✖ No review yet. Run `rwo inventory` first.")
        return 1
    d = collect(root, state)
    md = write_md(root, state, d)
    hp = write_html(root, state, d)
    state["summary_at"] = state.get("project", {}).get("pulled_at")
    st.save(state, root)
    task("update", "Final summary", "completed")
    t = d["totals"]
    emit(f"✔ Summary ready: {t['blocking']} blocking, {t['fix-before-production']} fix before production, "
         f"{t['optional']} optional · review/SUMMARY.html")
    print(f"SUMMARY_HTML {os.path.relpath(hp, root)}")
    print(f"SUMMARY_MD {os.path.relpath(md, root)}")
    return 0
