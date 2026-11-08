"""rwo summary: build review/SUMMARY.md and review/SUMMARY.html from the recorded data (nothing invented).

The HTML page is for managers and for the technical team: an executive overview first, then one section per
workflow with its diagram, steps, findings and every deliverable linked, so nobody has to search the folder.
"""
import base64, datetime, glob, html, json, os
from collections import Counter, OrderedDict
from . import __version__, state as st
from .progress import emit, task

LEVELS = [("blocking", "Blocking"), ("fix-before-production", "Fix before production"), ("optional", "Optional")]
LABEL = dict(LEVELS, **{"no-change-needed": "No change needed", "pending": "Not reviewed yet"})
READY = {"not-ready": "Not ready for production", "after-fixes": "Ready after fixes", "ready": "Ready", "pending": "Review not finished"}
MAX_EMBED = 4 * 1024 * 1024


def _rel(*parts):
    """Path relative to review/ (where SUMMARY.html lives), with forward slashes."""
    return "/".join(p.strip("/") for p in parts if p)


def _exists(root, rel):
    return os.path.exists(os.path.join(root, st.REVIEW_DIR, rel))


def readiness(c, pending):
    if pending:
        return "pending"
    if c["blocking"]:
        return "not-ready"
    return "after-fixes" if c["fix-before-production"] else "ready"


def collect(root, state):
    work = os.path.join(root, st.REVIEW_DIR, "work")
    answers = {os.path.basename(p)[:-len(".step.json")]: json.load(open(p, encoding="utf-8"))
               for p in glob.glob(os.path.join(work, "*.step.json"))}
    d = {"workflows": [], "blocking": [], "assumptions": OrderedDict(), "questions": OrderedDict(),
         "institutions": set(), "seconds": 0, "totals": Counter(), "steps": 0, "pending": 0, "scenarios": 0,
         "n_questions": 0}
    for wf in state["workflows"]:
        if not wf.get("in_scope", True):
            continue
        base = wf["dir"]
        w = {"key": wf["key"], "name": wf["name"], "dir": base, "triggers": wf.get("triggers", []),
             "counts": Counter(), "steps": [], "pending": 0, "adaptors": set(), "questions": 0,
             "png": _rel(base, "diagram", base + ".png"), "bpmn": _rel(base, "diagram", base + ".bpmn"),
             "changes": _rel(base, "proposed", "CHANGES.md"),
             "yaml": _rel(base, "proposed", wf.get("yaml", "")) if wf.get("yaml") else None}
        for k in ("png", "bpmn", "changes", "yaml"):
            if w[k] and not _exists(root, w[k]):
                w[k] = None
        w["png_data"] = None
        if w["png"]:
            full = os.path.join(root, st.REVIEW_DIR, w["png"])
            if os.path.getsize(full) <= MAX_EMBED:
                w["png_data"] = "data:image/png;base64," + base64.b64encode(open(full, "rb").read()).decode()
        for s in wf["steps"]:
            if not s.get("in_scope", True):
                continue
            d["steps"] += 1
            done = s.get("status") == "done"
            w["pending"] += not done
            if done and s.get("started_at") and s.get("done_at"):
                d["seconds"] += s["done_at"] - s["started_at"]
            counts = s.get("counts") or {}
            for k, _ in LEVELS:
                w["counts"][k] += counts.get(k, 0)
            if s.get("adaptor"):
                w["adaptors"].add(s["adaptor"].replace("@openfn/", ""))
            guide = os.path.relpath(s["guide"], st.REVIEW_DIR).replace(os.sep, "/") if s.get("guide") else None
            code = _rel(base, "proposed", s["file"])
            code = code if _exists(root, code) else None
            ans = answers.get(f"{wf['key']}-{s['n']:02d}-{s['id']}", {})
            step = {"n": s["n"], "name": s["name"], "priority": s.get("priority") if done else "pending",
                    "counts": counts, "guide": guide, "code": code, "summary": ans.get("summary", ""),
                    "findings": ans.get("findings", []), "adaptor": s.get("adaptor", "")}
            w["steps"].append(step)
            for f in step["findings"]:
                if f.get("priority") == "blocking":
                    d["blocking"].append({"wf": wf["key"], "wf_name": wf["name"], "step": s["name"],
                                          "title": f.get("title", ""), "today": f.get("today", ""),
                                          "change": f.get("change", ""), "guide": guide, "code": code})
            for a in ans.get("assumptions", []):
                d["assumptions"].setdefault(f"{wf['key']} · {wf['name']}", []).append((s["name"], a))
            for q in ans.get("questions", []):
                d["questions"].setdefault(q.get("owner", "client").strip(), []).append((wf["key"], s["name"], q.get("text", "")))
                d["n_questions"] += 1
                w["questions"] += 1
        sp = os.path.join(work, f"{wf['key']}.scenarios.json")
        w["tests"] = None
        if os.path.exists(sp):
            spec = json.load(open(sp, encoding="utf-8"))
            sc = spec.get("scenarios", [])
            w["tests"] = {"n": len(sc), "by_priority": Counter(x.get("priority") for x in sc),
                          "categories": sorted({x.get("category") for x in sc}),
                          "institutions": sorted({g.get("institution") for g in spec.get("institution_guides") or []})}
            d["scenarios"] += len(sc)
        d["totals"].update(w["counts"])
        d["pending"] += w["pending"]
        w["ready"] = readiness(w["counts"], w["pending"])
        w["adaptors"] = sorted(w["adaptors"])
        d["institutions"] |= set(wf.get("institutions") or [])
        d["workflows"].append(w)
    d["institutions"] = sorted(d["institutions"])
    d["minutes"] = max(1, round(d["seconds"] / 60)) if d["seconds"] else 0
    d["links"] = {k: v for k, v in (("tests", "tests/test-scenarios.xlsx"), ("questions", "questions.md"),
                                    ("inventory", "inventory.md"), ("progress", "progress.md"), ("md", "SUMMARY.md"))
                  if _exists(root, v) or k == "md"}
    return d


def verdict(d):
    t, n = d["totals"], len(d["workflows"])
    if d["pending"]:
        return "pending", f"Review not finished: {d['pending']} of {d['steps']} steps are still pending."
    nb = sum(1 for w in d["workflows"] if w["counts"]["blocking"])
    if t["blocking"]:
        return "not-ready", (f"Not ready for production: {t['blocking']} blocking issue{'s' if t['blocking'] != 1 else ''} in {nb} of {n} workflow{'s' if n != 1 else ''}. "
                             "Fix them first, then test the proposed code in a Lightning sandbox.")
    if t["fix-before-production"]:
        return "after-fixes", (f"Ready after fixes: no blocking issues, {t['fix-before-production']} items to fix "
                               "before production.")
    return "ready", "Ready: no blocking issues and nothing to fix before production."


def env_text(state):
    return {"yes": "test environments", "no": "production (be careful)"}.get(state.get("env_answer"),
                                                                           state.get("env_answer") or "not answered")


def lightning_url(p):
    return f"{p['endpoint']}/projects/{p['uuid']}/w" if p.get("endpoint") and p.get("uuid") else None


# ---------------------------------------------------------------- Markdown

def write_md(root, state, d):
    p = state.get("project", {})
    t = d["totals"]
    _, v = verdict(d)
    out = [f"# Workflow review: {p.get('name', '')}", "", f"**{v}**", "",
           f"- **Lightning project:** {lightning_url(p) or p.get('endpoint', '')}",
           f"- **Downloaded:** {p.get('pulled_at', '')} · **Credentials point to:** {env_text(state)} · "
           f"**Review time:** about {d['minutes']} min",
           f"- **Workflows / steps:** {len(d['workflows'])} / {d['steps']} · **Test scenarios:** {d['scenarios']} · "
           f"**Questions for the client:** {d['n_questions']}", "",
           "## Issues by workflow", "",
           "| Workflow | Status | Steps | Blocking | Fix before production | Optional | Diagram | Lucidchart file |",
           "|---|---|---|---|---|---|---|---|"]
    for w in d["workflows"]:
        c = w["counts"]
        out.append(f"| {w['key']} · {w['name']} | {READY[w['ready']]} | {len(w['steps'])} | {c['blocking']} | "
                   f"{c['fix-before-production']} | {c['optional']} | "
                   + (f"[PNG]({w['png']})" if w["png"] else "–") + " | "
                   + (f"[.bpmn]({w['bpmn']})" if w["bpmn"] else "–") + " |")
    out += [f"| **Total** | | **{d['steps']}** | **{t['blocking']}** | **{t['fix-before-production']}** | "
            f"**{t['optional']}** | | |", "", "## Blocking issues", ""]
    out += [f"- **{b['wf']} · {b['step']}: {b['title']}.** {b['today']}"
            + (f" ([change guide]({b['guide']}))" if b["guide"] else "")
            + (f" ([proposed code]({b['code']}))" if b["code"] else "") for b in d["blocking"]] or ["None."]
    out += ["", "## Deliverables", ""]
    if "tests" in d["links"]:
        out.append("- Test scenarios and institution guides: [tests/test-scenarios.xlsx](tests/test-scenarios.xlsx)")
    if "questions" in d["links"]:
        out.append(f"- Questions for the client ({d['n_questions']}): [questions.md](questions.md)")
    if "inventory" in d["links"]:
        out.append("- Inventory of the project: [inventory.md](inventory.md)")
    for w in d["workflows"]:
        parts = [f"[{x}]({y})" for x, y in (("diagram", w["png"]), ("Lucidchart file", w["bpmn"]),
                                            ("CHANGES.md", w["changes"])) if y]
        out.append(f"- {w['key']} · {w['name']}: " + (", ".join(parts) or "–"))
    out += ["", "## Import a diagram into Lucidchart", ""] + [f"{i}. {x}" for i, x in enumerate(LUCID, 1)]
    out += ["", "## Assumptions to confirm", ""]
    for wf, items in d["assumptions"].items():
        out += [f"- **{wf} · {s}:** {a}" for s, a in items]
    if not d["assumptions"]:
        out.append("None.")
    out += ["", "## Partner institutions found in the code (correct them if needed)", ""]
    out += [f"- {i}" for i in d["institutions"]] or ["None recorded."]
    if state.get("pending_changes"):
        out += ["", "## Changes since the previous review", ""] + [f"- {c}" for c in state["pending_changes"]]
    out += ["", "## What to do next", ""] + [f"{i}. {x}" for i, (x, _) in enumerate(NEXT, 1)]
    path = os.path.join(root, st.REVIEW_DIR, "SUMMARY.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return path


LUCID = ["Open Lucidchart (lucid.app) and sign in.",
         "Create a new, blank Lucidchart document (any folder or project is fine).",
         "Choose File → Import, pick the BPMN 2.0 option and select the workflow's .bpmn file (menu names can vary "
         "slightly between Lucid versions).",
         "Lucid draws the pool, the lanes, the steps, the arrows and the notes. Compare it with the PNG: the legend, "
         "the green fill of the notes and the large title only exist in the PNG, so add them in Lucid if you need them.",
         "Rename the document after the workflow and share it with the team."]

NEXT = [("Read the change guide of each blocking issue.", "blocking"),
        ("Test the proposed code in a Lightning sandbox (never in production), with invented data.", "workflows"),
        ("Import each .bpmn into Lucidchart and check it against the PNG.", "lucid"),
        ("Upload test-scenarios.xlsx to Google Drive and choose File → Save as Google Sheets; share the institution tabs.", "tests"),
        ("Send the questions for the client and record the answers.", "questions")]

# ---------------------------------------------------------------- HTML

CSS = """
:root{--bg:#f5f6f8;--card:#fff;--fg:#1d2330;--muted:#5d6678;--line:#e3e6ec;--accent:#3949ab;--accent-bg:#e8eaf6;
--block:#c62828;--block-bg:#fdecec;--fix:#a35f00;--fix-bg:#fff2d9;--opt:#56657a;--opt-bg:#e9eef4;--ok:#2e7d32;--ok-bg:#e4f4e5;--pend:#6b7280;--pend-bg:#eef0f3}
@media (prefers-color-scheme:dark){:root{--bg:#121519;--card:#1c2129;--fg:#e8ebf0;--muted:#a3abba;--line:#2d3440;--accent:#9fa8ff;--accent-bg:#252b45;
--block:#ff8a80;--block-bg:#3b1f22;--fix:#ffc266;--fix-bg:#3a2e17;--opt:#b4c0d0;--opt-bg:#283141;--ok:#81c784;--ok-bg:#1d3221;--pend:#a3abba;--pend-bg:#2a2f38}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1080px;margin:0 auto;padding:0 16px 56px}a{color:var(--accent)}h2{font-size:19px;margin:36px 0 12px;scroll-margin-top:60px}h3{margin:0;font-size:17px}
header{padding:28px 0 8px}header h1{font-size:28px;margin:0}header p{margin:4px 0 0;color:var(--muted)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:3px 12px;font-size:13px;color:var(--muted)}
.chip a{text-decoration:none}nav{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);margin:0 -16px;padding:8px 16px;display:flex;gap:16px;overflow-x:auto;white-space:nowrap;font-size:14px}
nav a{color:var(--muted);text-decoration:none}nav a:hover{color:var(--accent)}
.verdict{margin-top:18px;border-radius:12px;padding:14px 18px;font-weight:600;border-left:6px solid}
.verdict.not-ready{background:var(--block-bg);border-color:var(--block);color:var(--block)}.verdict.after-fixes{background:var(--fix-bg);border-color:var(--fix);color:var(--fix)}
.verdict.ready{background:var(--ok-bg);border-color:var(--ok);color:var(--ok)}.verdict.pending{background:var(--pend-bg);border-color:var(--pend);color:var(--pend)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:14px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;text-decoration:none;color:inherit}.kpi b{display:block;font-size:28px;line-height:1.2}
.kpi span{color:var(--muted);font-size:13px}.kpi.block b{color:var(--block)}.kpi.fix b{color:var(--fix)}.kpi.opt b{color:var(--opt)}
.links{display:flex;flex-wrap:wrap;gap:8px}.btn{display:inline-flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 12px;font-size:14px;text-decoration:none;color:var(--fg)}
.btn:hover{border-color:var(--accent);color:var(--accent)}.btn.primary{background:var(--accent-bg);border-color:transparent;color:var(--accent);font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:14px}
.card-head{display:flex;flex-wrap:wrap;align-items:center;gap:10px;justify-content:space-between}.meta{color:var(--muted);font-size:14px}
.mix{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--ok-bg);min-width:80px}.mix i{display:block}.mix .b{background:var(--block)}.mix .f{background:var(--fix)}.mix .o{background:var(--opt)}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:8px 6px;border-top:1px solid var(--line);vertical-align:middle}th{color:var(--muted);font-weight:600;font-size:13px}
td.n{text-align:right;font-variant-numeric:tabular-nums}.wrap{overflow-x:auto}
.badge{display:inline-block;padding:1px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.blocking,.not-ready{color:var(--block);background:var(--block-bg)}.fix-before-production,.after-fixes{color:var(--fix);background:var(--fix-bg)}
.optional{color:var(--opt);background:var(--opt-bg)}.no-change-needed,.ready{color:var(--ok);background:var(--ok-bg)}.pending{color:var(--pend);background:var(--pend-bg)}
.issue{border-left:4px solid var(--block);background:var(--card);border-radius:10px;padding:12px 16px;margin-bottom:10px;border-top:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
.issue p{margin:6px 0}.issue .where{color:var(--muted);font-size:13px}
figure{margin:14px 0 6px}figure img{width:100%;height:auto;border:1px solid var(--line);border-radius:8px;background:#fff}figcaption{font-size:13px;color:var(--muted);margin-top:4px}
details{border-top:1px solid var(--line)}details>summary{cursor:pointer;list-style:none;padding:9px 2px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
details>summary::-webkit-details-marker{display:none}details>summary:before{content:"▸";color:var(--muted);width:12px}details[open]>summary:before{content:"▾"}
.step-body{padding:0 4px 12px 22px}.finding{margin:8px 0;padding-left:10px;border-left:3px solid var(--line)}.finding p{margin:2px 0}.small{font-size:13px}
.howto{background:var(--accent-bg);border-radius:12px;padding:14px 18px}.howto ol{margin:8px 0 0;padding-left:20px}.howto li{margin:4px 0}
ul.check{list-style:none;padding:0;margin:0}ul.check li{padding:7px 0;border-top:1px solid var(--line)}ul.check li:before{content:"☐  ";color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}footer{margin-top:40px;color:var(--muted);font-size:13px}
@media print{nav{display:none}details{border:0}details>summary:before{content:""}.card,.issue{break-inside:avoid}}
"""


def _badge(cls, text):
    return f"<span class='badge {html.escape(cls)}'>{html.escape(text)}</span>"


def _mix(c):
    tot = sum(c[k] for k, _ in LEVELS) or 1
    return ("<div class='mix' role='img' aria-label='priority mix'>"
            + "".join(f"<i class='{cl}' style='width:{100 * c[k] / tot:.1f}%'></i>"
                      for k, cl in (("blocking", "b"), ("fix-before-production", "f"), ("optional", "o")))
            + "</div>")


def _btn(href, text, primary=False):
    return f"<a class='btn{' primary' if primary else ''}' href='{html.escape(href)}'>{html.escape(text)}</a>" if href else ""


def write_html(root, state, d):
    e = html.escape
    p = state.get("project", {})
    t = d["totals"]
    vcls, vtext = verdict(d)
    L = d["links"]
    lurl = lightning_url(p)
    h = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>Workflow review: {e(p.get('name', ''))}</title><style>{CSS}</style></head><body><main>",
         "<header>", f"<h1>Workflow review: {e(p.get('name', ''))}</h1>"]
    if p.get("description"):
        h.append(f"<p>{e(p['description'])}</p>")
    chips = [f"<a href='{e(lurl)}'>Open the project in Lightning ↗</a>" if lurl else e(p.get("endpoint", "")),
             f"Downloaded {e(p.get('pulled_at', ''))}", f"Credentials: {e(env_text(state))}",
             f"Review time: about {d['minutes']} min"]
    h.append("<div class='chips'>" + "".join(f"<span class='chip'>{c}</span>" for c in chips if c) + "</div></header>")
    nav = [("overview", "Overview"), ("blocking", "Blocking issues"), ("workflows", "Workflows"),
           ("lucid", "Lucidchart"), ("tests", "Tests"), ("questions", "Questions"), ("assumptions", "Assumptions"),
           ("next", "Next steps")]
    h.append("<nav>" + "".join(f"<a href='#{a}'>{b}</a>" for a, b in nav) + "</nav>")

    # Overview (managers)
    h += [f"<h2 id='overview'>Overview</h2><div class='verdict {vcls}'>{e(vtext)}</div>", "<div class='kpis'>",
          f"<a class='kpi' href='#workflows'><b>{len(d['workflows'])}</b><span>Workflows</span></a>",
          f"<a class='kpi' href='#workflows'><b>{d['steps']}</b><span>Steps reviewed</span></a>",
          f"<a class='kpi block' href='#blocking'><b>{t['blocking']}</b><span>Blocking</span></a>",
          f"<a class='kpi fix' href='#workflows'><b>{t['fix-before-production']}</b><span>Fix before production</span></a>",
          f"<a class='kpi opt' href='#workflows'><b>{t['optional']}</b><span>Optional</span></a>",
          f"<a class='kpi' href='#tests'><b>{d['scenarios']}</b><span>Test scenarios</span></a>",
          f"<a class='kpi' href='#questions'><b>{d['n_questions']}</b><span>Questions for the client</span></a></div>"]
    h.append("<div class='card' style='margin-top:14px'><div class='wrap'><table><tr><th>Workflow</th><th>Status</th>"
             "<th>Trigger</th><th class='n'>Steps</th><th class='n'>Blocking</th><th class='n'>Fix before prod.</th>"
             "<th class='n'>Optional</th><th>Mix</th></tr>")
    for w in d["workflows"]:
        c = w["counts"]
        h.append(f"<tr><td><a href='#{e(w['key'])}'>{e(w['key'])} · {e(w['name'])}</a></td>"
                 f"<td>{_badge(w['ready'], READY[w['ready']])}</td><td class='small'>{e(', '.join(w['triggers']))}</td>"
                 f"<td class='n'>{len(w['steps'])}</td><td class='n'>{c['blocking']}</td>"
                 f"<td class='n'>{c['fix-before-production']}</td><td class='n'>{c['optional']}</td><td>{_mix(c)}</td></tr>")
    h.append("</table></div></div>")
    h.append("<div class='links'>" + _btn(L.get("tests"), "📊 Test scenarios (.xlsx)", True)
             + _btn(L.get("questions"), "❓ Questions for the client") + _btn(L.get("inventory"), "📋 Inventory")
             + "".join(_btn(w["bpmn"], f"🧭 {w['key']} Lucidchart file") for w in d["workflows"])
             + _btn(L.get("md"), "📝 This summary as Markdown") + "</div>")

    # Blocking issues
    h.append(f"<h2 id='blocking'>Blocking issues: fix these first ({t['blocking']})</h2>")
    for b in d["blocking"]:
        h.append(f"<div class='issue'><div class='where'>{e(b['wf'])} · {e(b['wf_name'])} › {e(b['step'])}</div>"
                 f"<b>{e(b['title'])}</b><p>{e(b['today'])}</p>"
                 + (f"<p class='small'><b>Proposed change:</b> {e(b['change'])}</p>" if b["change"] else "")
                 + "<div class='links'>" + _btn(b["guide"], "Change guide") + _btn(b["code"], "Proposed code") + "</div></div>")
    if not d["blocking"]:
        h.append("<p>None.</p>")

    # Workflows (technical)
    h.append("<h2 id='workflows'>Workflows</h2>")
    for w in d["workflows"]:
        c = w["counts"]
        h.append(f"<div class='card' id='{e(w['key'])}'><div class='card-head'><h3>{e(w['key'])} · {e(w['name'])}</h3>"
                 f"{_badge(w['ready'], READY[w['ready']])}</div>"
                 f"<div class='meta'>{e(', '.join(w['triggers']))} · {len(w['steps'])} steps · {c['blocking']} blocking, "
                 f"{c['fix-before-production']} fix before production, {c['optional']} optional"
                 + (f" · adaptors: {e(', '.join(w['adaptors']))}" if w["adaptors"] else "") + "</div>")
        if w["png_data"]:
            h.append(f"<figure><a href='{e(w['png'])}'><img src='{w['png_data']}' alt='Diagram of {e(w['name'])}' loading='lazy'></a>"
                     "<figcaption>Proposed workflow diagram (OpenFn house style). Click to open the PNG; import the "
                     ".bpmn file into Lucidchart to edit it.</figcaption></figure>")
        h.append("<div class='links'>" + _btn(w["bpmn"], "🧭 Lucidchart file (.bpmn)", True) + _btn(w["png"], "🖼 Diagram (.png)")
                 + _btn(w["changes"], "📄 CHANGES.md") + _btn(w["yaml"], "⚙ Proposed workflow.yaml")
                 + (_btn(L.get("tests"), f"📊 {w['tests']['n']} test scenarios") if w["tests"] and L.get("tests") else "")
                 + "</div><div style='margin-top:10px'>")
        for s in w["steps"]:
            pr = s["priority"] or "pending"
            n = sum((s["counts"] or {}).values())
            h.append(f"<details><summary><b>{s['n']}. {e(s['name'])}</b> {_badge(pr, LABEL.get(pr, pr))}"
                     f"<span class='meta'>{n} issue{'s' if n != 1 else ''}</span></summary><div class='step-body'>")
            if s["summary"]:
                h.append(f"<p>{e(s['summary'])}</p>")
            for f in s["findings"]:
                fp = f.get("priority", "optional")
                h.append(f"<div class='finding'><p>{_badge(fp, LABEL.get(fp, fp))} <b>{e(f.get('title', ''))}</b></p>"
                         f"<p class='small'><b>Today:</b> {e(f.get('today', ''))}</p>"
                         f"<p class='small'><b>Change:</b> {e(f.get('change', ''))}</p></div>")
            h.append("<div class='links'>" + _btn(s["guide"], "Change guide") + _btn(s["code"], "Proposed code (.js)")
                     + "</div>" + (f"<p class='small meta'>Adaptor: {e(s['adaptor'])}</p>" if s["adaptor"] else "")
                     + "</div></details>")
        h.append("</div></div>")

    # Lucidchart
    h.append("<h2 id='lucid'>Import the diagrams into Lucidchart</h2><div class='howto'>"
             "<b>Each workflow has a .bpmn file made for Lucidchart and a PNG preview.</b><ol>"
             + "".join(f"<li>{e(x)}</li>" for x in LUCID) + "</ol><div class='links' style='margin-top:10px'>"
             + "".join(_btn(w["bpmn"], f"{w['key']} · {w['name']} (.bpmn)") for w in d["workflows"]) + "</div></div>")

    # Tests
    h.append("<h2 id='tests'>Test plan</h2><div class='card'>")
    if L.get("tests"):
        h.append(f"<p>{d['scenarios']} scenarios to run in a Lightning sandbox, plus one guide tab per partner institution "
                 "with what they do before, during and after each test.</p><div class='links'>"
                 + _btn(L["tests"], "📊 Open test-scenarios.xlsx", True) + "</div>")
        h.append("<div class='wrap' style='margin-top:10px'><table><tr><th>Workflow</th><th class='n'>Scenarios</th>"
                 "<th class='n'>Blocking</th><th class='n'>Fix before prod.</th><th class='n'>Optional</th><th>Categories</th>"
                 "<th>Institution guides</th></tr>")
        for w in d["workflows"]:
            ts = w["tests"]
            if not ts:
                h.append(f"<tr><td>{e(w['key'])} · {e(w['name'])}</td><td colspan='6' class='meta'>No scenarios yet</td></tr>")
                continue
            bp = ts["by_priority"]
            h.append(f"<tr><td>{e(w['key'])} · {e(w['name'])}</td><td class='n'>{ts['n']}</td><td class='n'>{bp.get('blocking', 0)}</td>"
                     f"<td class='n'>{bp.get('fix-before-production', 0)}</td><td class='n'>{bp.get('optional', 0)}</td>"
                     f"<td class='small'>{e(', '.join(ts['categories']))}</td><td class='small'>{e(', '.join(ts['institutions'])) or '–'}</td></tr>")
        h.append("</table></div><p class='small meta'>To share it: upload the file to Google Drive, open it and choose "
                 "File → Save as Google Sheets.</p>")
    else:
        h.append("<p class='meta'>The test spreadsheet has not been generated yet.</p>")
    h.append("</div>")

    # Questions
    h.append(f"<h2 id='questions'>Questions for the client ({d['n_questions']})</h2><div class='card'>")
    for owner, qs in d["questions"].items():
        h.append(f"<details><summary><b>{e(owner)}</b><span class='meta'>{len(qs)} question{'s' if len(qs) != 1 else ''}</span>"
                 "</summary><ol class='step-body'>"
                 + "".join(f"<li><span class='meta'>{e(k)} · {e(s)}:</span> {e(q)}</li>" for k, s, q in qs) + "</ol></details>")
    if not d["questions"]:
        h.append("<p>None.</p>")
    h.append("<div class='links' style='margin-top:10px'>" + _btn(L.get("questions"), "Open questions.md (ready for email)") + "</div></div>")

    # Assumptions and institutions
    n_ass = sum(len(v) for v in d["assumptions"].values())
    h.append(f"<h2 id='assumptions'>Assumptions to confirm ({n_ass})</h2><div class='card'>")
    for wf, items in d["assumptions"].items():
        h.append(f"<details><summary><b>{e(wf)}</b><span class='meta'>{len(items)}</span></summary><ul class='step-body'>"
                 + "".join(f"<li><span class='meta'>{e(s)}:</span> {e(a)}</li>" for s, a in items) + "</ul></details>")
    if not d["assumptions"]:
        h.append("<p>None.</p>")
    h.append(f"<p class='small' style='margin-top:12px'><b>Partner institutions found in the code:</b> "
             f"{e(', '.join(d['institutions'])) or 'none recorded'} <span class='meta'>(correct them if needed)</span></p></div>")
    if state.get("pending_changes"):
        h.append("<h2>Changes since the previous review</h2><div class='card'><ul>"
                 + "".join(f"<li>{e(c)}</li>" for c in state["pending_changes"]) + "</ul></div>")

    # Next steps
    targets = {"blocking": "#blocking", "workflows": "#workflows", "lucid": "#lucid", "tests": L.get("tests"),
               "questions": L.get("questions")}
    h.append("<h2 id='next'>Next steps</h2><div class='card'><ul class='check'>"
             + "".join(f"<li>{e(x)} " + (f"<a href='{e(targets[k])}'>Go</a>" if targets.get(k) else "") + "</li>" for x, k in NEXT)
             + "</ul></div>")
    h.append(f"<footer>Generated by OpenFn Workflow Review {__version__} on {datetime.date.today().isoformat()}. "
             "Proposals only: nothing was changed, deployed or run in Lightning. The links open the files in the review "
             "folder: open this page from that folder for them to work.</footer></main></body></html>")
    path = os.path.join(root, st.REVIEW_DIR, "SUMMARY.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(h))
    return path


def run(root):
    state = st.load(root)
    if not state or not state.get("workflows"):
        emit("✖ No review yet. Run `rwo inventory` first.")
        return 1
    if not state.get("project", {}).get("name") or not state["project"].get("endpoint"):
        from .inventory import project_info
        info = project_info(root)
        state["project"] = {**state.get("project", {}), **{k: v for k, v in info.items() if v and not state.get("project", {}).get(k)}}
    d = collect(root, state)
    md = write_md(root, state, d)
    hp = write_html(root, state, d)
    st.save(state, root)
    task("update", "Final summary", "completed")
    t = d["totals"]
    emit(f"✔ Summary ready: {t['blocking']} blocking, {t['fix-before-production']} fix before production, "
         f"{t['optional']} optional · review/SUMMARY.html")
    print(f"SUMMARY_HTML {os.path.relpath(hp, root)}")
    print(f"SUMMARY_MD {os.path.relpath(md, root)}")
    return 0
