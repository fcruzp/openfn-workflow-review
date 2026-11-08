"""Lay out a workflow diagram in the validated house style (Demo 3).

The model only provides lanes.json (lanes, labels, kinds, endpoints, results, notes).
Everything about positions, sizes and colors is decided here, the same way every time.
"""
import json, os, textwrap
from collections import deque

STYLE = json.load(open(os.path.join(os.path.dirname(__file__), "style", "bpmn-style.json"), encoding="utf-8"))
S = STYLE["sizes"]
KINDS = ("institutional", "notification", "indicator", "internal")


class Shape(dict):
    """A drawable element: id, type, x, y, w, h, label, fill, lane, plus extras."""
    @property
    def cx(self): return self["x"] + self["w"] / 2
    @property
    def cy(self): return self["y"] + self["h"] / 2
    @property
    def right(self): return self["x"] + self["w"]
    @property
    def bottom(self): return self["y"] + self["h"]


def wrap(text, width_px, char_px=7.2):
    return textwrap.wrap(text, max(10, int(width_px / char_px))) or [""]


def validate(spec, wf_yaml):
    errs = []
    steps = {s["id"]: s for s in wf_yaml.get("steps", []) if s.get("expression")}
    lanes = spec.get("lanes") or []
    if spec.get("openfn_lane") not in lanes:
        errs.append("`openfn_lane` must be one of `lanes`.")
    for sid, st in (spec.get("steps") or {}).items():
        if sid not in steps:
            errs.append(f"Unknown step id `{sid}` (use the step ids from the workflow file).")
        if st.get("kind", "internal") not in KINDS:
            errs.append(f"Step `{sid}`: kind must be one of {KINDS}.")
        for k in ("result", "reads"):
            if st.get(k) and st[k].get("lane") not in lanes:
                errs.append(f"Step `{sid}`: {k}.lane must be one of `lanes`.")
    missing = [sid for sid in steps if sid not in (spec.get("steps") or {})]
    if missing:
        errs.append("Every step needs an entry in `steps`. Missing: " + ", ".join(missing))
    for n in spec.get("notes", []):
        if n.get("lane") not in lanes:
            errs.append(f"Note \"{n.get('title', '')}\": lane must be one of `lanes`.")
    return errs


def build(spec, wf_yaml):
    """Return a layout dict: shapes, flows, associations, lanes, pool, legend, title, canvas bounds."""
    lanes = spec["lanes"]
    openfn = spec["openfn_lane"]
    all_steps = wf_yaml.get("steps", [])
    by_id = {s["id"]: s for s in all_steps}
    trigger = next((s for s in all_steps if s.get("type") in ("cron", "webhook", "kafka")), None)
    jobs = [s for s in all_steps if s.get("expression")]
    children = {s["id"]: [n for n in (s.get("next") or {}) if n in by_id and by_id[n].get("expression")]
                for s in all_steps}
    edge_info = {(s["id"], n): (e or {}) for s in all_steps for n, e in (s.get("next") or {}).items()}

    # 1. Columns and rows (rows are vertical offsets in px from the main line).
    col, row = {}, {}
    start_children = children.get(trigger["id"], []) if trigger else ([jobs[0]["id"]] if jobs else [])
    q = deque()
    for i, c in enumerate(start_children):
        col[c], row[c] = 1, (i - (len(start_children) - 1) / 2) * S["branch_pitch"]
        q.append(c)
    gateways = {}
    while q:
        sid = q.popleft()
        kids = children.get(sid, [])
        extra = 0
        if len(kids) > 1:
            gateways[sid] = col[sid] + 1
            extra = 1
        for i, k in enumerate(kids):
            c = col[sid] + 1 + extra
            r = row[sid] + ((i - (len(kids) - 1) / 2) * S["branch_pitch"] if len(kids) > 1 else 0)
            if k not in col or c > col[k]:
                col[k], row[k] = c, row.get(k, r) if k in col else r
                q.append(k)
    for s in jobs:                              # unreachable steps: after the rest
        if s["id"] not in col:
            col[s["id"]], row[s["id"]] = max(col.values(), default=0) + 1, 0

    # 2. Lane heights.
    tw, th = S["task"]
    rows_used = [row[s] for s in col] or [0]
    span = max(rows_used) - min(rows_used)
    notes_by_lane = {}
    for n in spec.get("notes", []):
        notes_by_lane.setdefault(n["lane"], []).append(n)
    lane_h = {}
    for ln in lanes:
        if ln == openfn:
            lane_h[ln] = max(S["openfn_lane_min"], span + th + 330)
        else:
            lane_h[ln] = S["lane_min"] + (60 if notes_by_lane.get(ln) else 0)
    pool_x, pool_y = S["pool_x"], S["pool_y"]
    lane_x = pool_x + S["pool_label"]
    lane_y, y = {}, pool_y
    for ln in lanes:
        lane_y[ln] = y
        y += lane_h[ln]
    of_top = lane_y[openfn]
    main_y = of_top + max(160, -min(rows_used) + 120)   # top of the main-line tasks

    def col_x(c):
        return lane_x + 60 + c * S["column_pitch"] - S["column_pitch"] + 70

    shapes, flows, assocs, notes, reserved = [], [], [], [], []
    ids = {}

    def add(shape):
        shapes.append(shape)
        ids[shape["id"]] = shape
        return shape

    colors = STYLE["colors"]
    # 3. Start event.
    ew, eh = S["event"]
    start = add(Shape(id="start", type="startEvent", x=col_x(1) - 90, y=main_y + th / 2 - eh / 2, w=ew, h=eh,
                      label=spec.get("start_label") or ("Cron" if trigger and trigger.get("type") == "cron" else "Webhook"),
                      trigger=(trigger or {}).get("type", "webhook"), lane=openfn, fill=None))
    # 4. Tasks.
    for s in jobs:
        st = spec["steps"][s["id"]]
        kind = st.get("kind", "internal")
        t = add(Shape(id=f"task_{s['id']}", type="task", x=col_x(col[s["id"]]), y=main_y + row[s["id"]],
                      w=tw, h=th, label=st.get("label") or s.get("name", s["id"]), lane=openfn,
                      fill=colors[kind] if kind != "internal" else None, kind=kind))
        if st.get("endpoint"):
            w, h = S["endpoint"]
            add(Shape(id=f"ep_{s['id']}", type="endpoint", x=t["x"], y=t["y"] - h - 5, w=w, h=h,
                      label=st["endpoint"], lane=openfn, fill=None))
    # 5. Gateways.
    gw, gh = S["gateway"]
    for sid, c in gateways.items():
        src = ids[f"task_{sid}"]
        add(Shape(id=f"gw_{sid}", type="parallelGateway", x=src.right + (S["column_pitch"] - tw) / 2 + 10,
                  y=src.cy - gh / 2, w=gw, h=gh, label="", lane=openfn, fill=None))
    # 6. Sequence flows (+ end events after terminal steps).
    def link(a, b, label=""):
        flows.append({"id": f"flow_{len(flows) + 1}", "source": a["id"], "target": b["id"], "label": label})
    for c in start_children:
        link(start, ids[f"task_{c}"])
    for s in jobs:
        a = ids[f"task_{s['id']}"]
        kids = children.get(s["id"], [])
        if len(kids) > 1:
            g = ids[f"gw_{s['id']}"]
            link(a, g)
            a = g
        for k in kids:
            e = edge_info.get((s["id"], k), {})
            label = e.get("label") or ("Always" if e.get("condition") == "always" else "")
            link(a, ids[f"task_{k}"], label if len(kids) == 1 else (e.get("label") or ""))
        if not kids:
            end_label = (spec.get("ends") or {}).get(s["id"], "")
            add(Shape(id=f"end_{s['id']}", type="endEvent", x=a.right + S["end_gap"], y=a.cy - eh / 2, w=ew, h=eh,
                      label=end_label, lane=openfn, fill=colors["end"]))
            link(a, ids[f"end_{s['id']}"])
    # 7. Results in other lanes, and data read from other lanes (dotted associations).
    for s in jobs:
        st = spec["steps"][s["id"]]
        t = ids[f"task_{s['id']}"]
        if st.get("result"):
            ln = st["result"]["lane"]
            e = add(Shape(id=f"res_{s['id']}", type="endEvent", x=t.cx - ew / 2,
                          y=lane_y[ln] + lane_h[ln] / 2 - eh / 2 - 10, w=ew, h=eh,
                          label=st["result"].get("label", ""), lane=ln, fill=colors["end"]))
            assocs.append({"id": f"assoc_res_{s['id']}", "source": t["id"], "target": e["id"]})
        if st.get("reads"):
            ln = st["reads"]["lane"]
            dw, dh = S["data_object"]
            store = st["reads"].get("store", False)
            if store:
                dw, dh = S["data_store"]
            d = add(Shape(id=f"data_{s['id']}", type="dataStoreReference" if store else "dataObjectReference",
                          x=t["x"] - 70, y=lane_y[ln] + 30, w=dw, h=dh, label=st["reads"].get("label", ""),
                          lane=ln, fill=colors["indicator"] if store else None))
            assocs.append({"id": f"assoc_data_{s['id']}", "source": d["id"], "target": t["id"]})
            ex = t.right - 14   # enter the task near its right edge, clear of the endpoint label
            if d["y"] < t["y"]:
                reserved.append({"x": d.right, "y": d.cy - 4, "w": ex - d.right + 4, "h": 8})
                reserved.append({"x": ex - 4, "y": d.cy, "w": 8, "h": t["y"] - d.cy})
        if st.get("writes_store"):
            ln = st["writes_store"]["lane"]
            dw, dh = S["data_store"]
            d = add(Shape(id=f"store_{s['id']}", type="dataStoreReference", x=t.cx - dw / 2,
                          y=lane_y[ln] + 35, w=dw, h=dh, label=st["writes_store"].get("label", ""),
                          lane=ln, fill=colors["indicator"]))
            assocs.append({"id": f"assoc_store_{s['id']}", "source": t["id"], "target": d["id"]})

    # 8. Notes (green boxes), placed in free space of their lane (never over a dotted route).
    lane_w_content = max([sh.right for sh in shapes] + [lane_x + 600])
    def free(rect, pad=14):
        x, y0, w, h = rect
        for sh in shapes + notes + reserved:
            if not (x + w + pad < sh["x"] or sh["x"] + sh["w"] + pad < x or
                    y0 + h + pad < sh["y"] or sh["y"] + sh["h"] + pad < y0):
                return False
        return True
    for i, n in enumerate(spec.get("notes", [])):
        lines = [n.get("title", "")] + n.get("lines", [])
        w = S["note_width"] + (30 if max((len(l) for l in lines), default=0) > 60 else 0)
        wrapped = [wl for l in lines for wl in wrap(l, w - 20)]
        h = 16 + S["note_line"] * len(wrapped)
        ln = n["lane"]
        near = ids.get(f"task_{n['near']}") if n.get("near") else None
        x0 = (near["x"] - 40) if near else lane_x + 80
        placed = None
        y_start, y_end = lane_y[ln] + 15, lane_y[ln] + lane_h[ln] - h - 10
        for dx in range(0, 4000, 20):
            for x in (x0 + dx,):
                yy = y_start
                while yy <= max(y_start, y_end):
                    if free((x, yy, w, h)):
                        placed = (x, yy)
                        break
                    yy += 20
            if placed:
                break
        if not placed:   # grow the lane
            placed = (x0, lane_y[ln] + lane_h[ln] - 10)
        notes.append(Shape(id=f"note_{i + 1}", type="note", x=placed[0], y=placed[1], w=w, h=h,
                           lines=wrapped, title=n.get("title", ""), lane=ln, fill=colors["comment"]))
    # grow lanes that notes overflow, and shift everything below
    for ln in lanes:
        bottom = max([sh.bottom for sh in shapes + notes if sh["lane"] == ln] + [lane_y[ln]])
        need = bottom + 25 - (lane_y[ln] + lane_h[ln])
        if need > 0:
            lane_h[ln] += need
            idx = lanes.index(ln)
            for below in lanes[idx + 1:]:
                lane_y[below] += need
                for sh in shapes + notes:
                    if sh["lane"] == below:
                        sh["y"] += need
    width = max([sh.right for sh in shapes + notes] + [lane_w_content]) + S["margin_right"] - pool_x
    pool_h = sum(lane_h.values())
    legend_kinds = ["institutional", "notification", "comment"] + (["indicator"] if spec.get("indicators") else [])
    lang = spec.get("language", "en")
    lw, lh = S["legend_box"]
    legend = [Shape(id=f"legend_{k}", type="legend", x=20, y=-(len(legend_kinds) - i) * S["legend_pitch"] - 5,
                    w=lw, h=lh, label=STYLE["legend"][lang][k], fill=colors[k if k != "comment" else "comment"])
              for i, k in enumerate(legend_kinds)]
    title = Shape(id="title", type="title", x=20, y=0, w=width - 20, h=S["title_height"], label=spec["title"])
    return {"shapes": shapes, "notes": notes, "flows": flows, "assocs": assocs, "legend": legend, "title": title,
            "lanes": [{"name": ln, "x": lane_x, "y": lane_y[ln], "w": width - S["pool_label"], "h": lane_h[ln]}
                      for ln in lanes],
            "pool": {"name": spec.get("pool") or spec["title"], "x": pool_x, "y": pool_y, "w": width, "h": pool_h},
            "bounds": (0, legend[0]["y"] - 20, pool_x + width + 20, pool_y + pool_h + 20), "ids": ids}


def waypoints(lay, flow, kind="flow"):
    """Orthogonal route between two shapes."""
    a = lay["ids"].get(flow["source"]) or next(n for n in lay["notes"] if n["id"] == flow["source"])
    b = lay["ids"].get(flow["target"])
    if kind == "assoc":
        if b["type"] == "task" and a["type"] in ("dataObjectReference", "dataStoreReference"):
            ex = b.right - 14
            return [(a.right, a.cy), (ex, a.cy), (ex, b["y"] if b["y"] > a["y"] else b.bottom)]
        down = b["y"] > a["y"]
        return [(a.cx, a.bottom if down else a["y"]), (b.cx, b["y"] if down else b.bottom)]
    if abs(a.cy - b.cy) < 1:
        return [(a.right, a.cy), (b["x"], b.cy)]
    if a["type"] == "parallelGateway":
        return [(a.cx, a["y"] if b.cy < a.cy else a.bottom), (a.cx, b.cy), (b["x"], b.cy)]
    mid = (a.right + b["x"]) / 2
    return [(a.right, a.cy), (mid, a.cy), (mid, b.cy), (b["x"], b.cy)]
