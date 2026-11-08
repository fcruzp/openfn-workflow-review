"""rwo tests: validate a workflow's scenarios.json and (re)build review/tests/test-scenarios.xlsx.

The spreadsheet holds every workflow that has scenarios: one "Test scenarios" tab, then one guide tab
per partner institution (columns from the house standard). Each call stores the workflow's scenarios
in review/work/<WF>.scenarios.json, so the spreadsheet is always rebuilt from all of them.
"""
import os, json, glob, shutil
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from . import state as st
from .progress import emit, task
from .submit import NATIONAL_ID, PHONE
from .workflow import find, maybe_done

CATEGORIES = ["Normal flow", "Edge data", "Invalid data", "System failure", "Credentials",
              "OpenFn behavior", "Trigger", "Security and operations"]
PRIORITIES = {"blocking": "Blocking", "fix-before-production": "Fix before production", "optional": "Optional"}
PRIORITY_FILL = {"blocking": "F8D7DA", "fix-before-production": "FFE8B3", "optional": "E2E8F0"}
TAB_COLORS = ["BDE3FF", "A7D8F0", "C7E9FF", "9FCFEA", "D6EEFF", "B3DDF2"]   # light blues
HEADER_FILL = "1F3A5F"
SCENARIO_COLS = [("ID", 11), ("Workflow", 22), ("Step", 24), ("Category", 18), ("Priority", 18),
                 ("Scenario", 40), ("How to set it up (test data)", 45), ("Expected result", 45),
                 ("Institutions involved", 24), ("Status", 14), ("Tested by", 16), ("Date", 12), ("Notes", 30)]
GUIDE_COLS = [("ID", 11), ("Workflow", 22), ("Priority", 18), ("What we want to check", 38),
              ("Why we run this test", 38), ("Joint test?", 20), ("Before the test", 42),
              ("During the test", 42), ("After the test", 42), ("What to send the client", 34),
              ("Important note", 32)]
STATUSES = "Not started,Passed,Failed,Blocked"
EVIDENCE = "Screenshot showing the record ID, the date and the name of who checked."
THIN = Side(style="thin", color="B0B7C3")


def validate(spec, wf):
    errs = []
    if spec.get("workflow") != wf["name"]:
        errs.append(f'"workflow" must be exactly "{wf["name"]}".')
    steps = {s["name"] for s in wf["steps"]}
    scen = spec.get("scenarios") or []
    if not scen:
        errs.append('"scenarios" is empty: write at least one scenario.')
    refs = set()
    for i, sc in enumerate(scen, 1):
        where = f"scenario {i}"
        for k in ("ref", "category", "priority", "title", "setup", "expected"):
            if not str(sc.get(k, "")).strip():
                errs.append(f'{where}: "{k}" is missing.')
        if sc.get("ref") in refs:
            errs.append(f'{where}: "ref" {sc.get("ref")} is repeated.')
        refs.add(sc.get("ref"))
        if sc.get("category") not in CATEGORIES:
            errs.append(f'{where}: category must be one of: {", ".join(CATEGORIES)}.')
        if sc.get("priority") not in PRIORITIES:
            errs.append(f'{where}: priority must be one of: {", ".join(PRIORITIES)}.')
        if sc.get("step") and sc["step"] not in steps:
            errs.append(f'{where}: step "{sc["step"]}" does not exist (use the exact step name or null).')
        if sc.get("category") == "Credentials" and sc.get("institutions"):
            errs.append(f"{where}: credential tests need no institution (the client edits the test credential in Lightning).")
    for g in spec.get("institution_guides") or []:
        inst = str(g.get("institution", "")).strip()
        if not inst:
            errs.append('an institution guide has no "institution" name.')
        for j, t in enumerate(g.get("tests") or [], 1):
            where = f'guide "{inst}" test {j}'
            if t.get("ref") not in refs:
                errs.append(f'{where}: "ref" {t.get("ref")} is not a scenario ref.')
            for k in ("check", "why", "before", "during", "after"):
                if not t.get(k):
                    errs.append(f'{where}: "{k}" is missing.')
            for k in ("before", "during", "after"):
                if t.get(k) is not None and not isinstance(t[k], list):
                    errs.append(f'{where}: "{k}" must be a list of steps (the program numbers them).')
    for sc in scen:
        for inst in sc.get("institutions") or []:
            if not any(g.get("institution") == inst for g in spec.get("institution_guides") or []):
                errs.append(f'scenario {sc.get("ref")}: institution "{inst}" has no guide; add it to "institution_guides".')
    text = json.dumps(spec, ensure_ascii=False)
    for m in NATIONAL_ID.findall(text):
        if m != "000-0000000-0":
            errs.append(f"Personal data: a national ID ({m[:3]}…). Use invented data like 000-0000000-0.")
    if PHONE.search(text):
        errs.append("Personal data: a Dominican phone number. Use an invented one like 555-0100.")
    return errs


def _header(ws, row, cols):
    for c, (name, width) in enumerate(cols, 1):
        cell = ws.cell(row=row, column=c, value=name)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=HEADER_FILL)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
        ws.column_dimensions[get_column_letter(c)].width = width
    ws.freeze_panes = ws.cell(row=row + 1, column=2)


def _row(ws, row, values, priority):
    for c, v in enumerate(values, 1):
        cell = ws.cell(row=row, column=c, value=v)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
    pcol = [i for i, (n, _) in enumerate(SCENARIO_COLS if ws.title == "Test scenarios" else GUIDE_COLS, 1)
            if n == "Priority"][0]
    ws.cell(row=row, column=pcol).fill = PatternFill("solid", fgColor=PRIORITY_FILL[priority])


def _numbered(items):
    return "\n".join(f"{i}. {x}" for i, x in enumerate(items, 1))


def _title(ws, title, text, ncols):
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=14)
    ws.cell(row=2, column=1, value=text).alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    ws.row_dimensions[2].height = 48


def build(root, state, project_name):
    specs = []
    for p in sorted(glob.glob(os.path.join(root, st.REVIEW_DIR, "work", "WF*.scenarios.json"))):
        specs.append(json.load(open(p, encoding="utf-8")))
    order = {w["key"]: i for i, w in enumerate(state["workflows"])}
    specs.sort(key=lambda s: order.get(s["_key"], 99))
    wb = Workbook()
    ws = wb.active
    ws.title = "Test scenarios"
    _title(ws, f"Test scenarios: {project_name}",
           "Every scenario to test in a Lightning sandbox before production, by workflow. Use invented test data "
           "only. Update Status, Tested by and Date as you go. The institution tabs explain what each partner "
           "institution has to do.", len(SCENARIO_COLS))
    _header(ws, 4, SCENARIO_COLS)
    dv = DataValidation(type="list", formula1=f'"{STATUSES}"', allow_blank=True)
    ws.add_data_validation(dv)
    ids, guides, r = {}, {}, 5
    for sp in specs:
        for n, sc in enumerate(sp["scenarios"], 1):
            sid = f"{sp['_key']}-T{n:02d}"
            ids[(sp["_key"], sc["ref"])] = (sid, sc)
            _row(ws, r, [sid, sp["workflow"], sc.get("step") or "Whole workflow", sc["category"],
                         PRIORITIES[sc["priority"]], sc["title"], sc["setup"], sc["expected"],
                         ", ".join(sc.get("institutions") or []) or "None (OpenFn / client team)",
                         "Not started", "", "", sc.get("notes", "")], sc["priority"])
            dv.add(ws.cell(row=r, column=10))
            r += 1
        for g in sp.get("institution_guides") or []:
            gi = guides.setdefault(g["institution"], {"intro": g.get("intro", ""), "rows": []})
            gi["intro"] = gi["intro"] or g.get("intro", "")
            for t in g.get("tests") or []:
                gi["rows"].append((sp, t))
    for i, (inst, g) in enumerate(guides.items()):
        gs = wb.create_sheet(_safe_title(f"Guide - {inst}", wb))
        gs.sheet_properties.tabColor = TAB_COLORS[i % len(TAB_COLORS)]
        _title(gs, f"Test guide for {inst}",
               g["intro"] or f"What {inst} has to do in each test: before, during and after. When the test is "
               "joint, agree on the same date and time with the other institution.", len(GUIDE_COLS))
        _header(gs, 4, GUIDE_COLS)
        r = 5
        for sp, t in g["rows"]:
            sid, sc = ids[(sp["_key"], t["ref"])]
            others = [x for x in sc.get("institutions") or [] if x != inst]
            joint = f"Yes, with {', '.join(others)}" if others else "No"
            _row(gs, r, [sid, sp["workflow"], PRIORITIES[sc["priority"]], t["check"], t["why"], joint,
                         _numbered(t["before"]), _numbered(t["during"]), _numbered(t["after"]),
                         t.get("evidence") or EVIDENCE, t.get("note", "")], sc["priority"])
            r += 1
    out = os.path.join(root, st.REVIEW_DIR, "tests", "test-scenarios.xlsx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wb.save(out)
    return out, sum(len(s["scenarios"]) for s in specs), list(guides)


def _safe_title(t, wb):
    for ch in '[]:*?/\\':
        t = t.replace(ch, "-")
    t = t[:31]
    base, k = t, 2
    while t in wb.sheetnames:
        t = f"{base[:28]} {k}"
        k += 1
    return t


def run(root, key, spec_path):
    state = st.load(root)
    wf = find(state, key)
    if not wf:
        emit(f"✖ Unknown workflow key {key}.")
        return 1
    try:
        spec = json.load(open(spec_path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        emit(f"✖ Can't read {spec_path}: {e}")
        return 1
    errs = validate(spec, wf)
    if errs:
        emit(f"✖ {key}: scenarios rejected. Fix these and run `rwo tests {key} {spec_path}` again:")
        for e in errs:
            print(f"  - {e}")
        return 1
    spec["_key"] = wf["key"]
    work = os.path.join(root, st.REVIEW_DIR, "work")
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, f"{wf['key']}.scenarios.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    out, n, insts = build(root, state, state.get("project", {}).get("name", ""))
    wf["tests"] = True
    wf["institutions"] = sorted({i for sc in spec["scenarios"] for i in sc.get("institutions") or []}
                                | {g["institution"] for g in spec.get("institution_guides") or []})
    maybe_done(state, wf)
    st.save(state, root)
    emit(f"✔ {key}: {len(spec['scenarios'])} test scenarios. Spreadsheet: {n} scenarios, "
         f"{len(insts)} institution guides · {os.path.relpath(out, root)}")
    return 0
