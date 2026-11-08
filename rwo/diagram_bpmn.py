"""Write a laid-out diagram as BPMN 2.0 XML (with layout and the colors BPMN can carry)."""
from xml.sax.saxutils import escape, quoteattr
from .diagram_layout import waypoints

NS = ('xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
      'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
      'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
      'xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" '
      'xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0"')


def color_attrs(fill):
    if not fill:
        return ""
    return (f' bioc:stroke="#000000" bioc:fill="{fill}" color:background-color="{fill}" '
            f'color:border-color="#000000"')


def bounds(sh):
    return f'<dc:Bounds x="{sh["x"]:.0f}" y="{sh["y"]:.0f}" width="{sh["w"]:.0f}" height="{sh["h"]:.0f}" />'


def label_bounds(sh):
    return (f'<bpmndi:BPMNLabel><dc:Bounds x="{sh["x"] - 32:.0f}" y="{sh["y"] + sh["h"] + 5:.0f}" '
            f'width="{sh["w"] + 64:.0f}" height="40" /></bpmndi:BPMNLabel>')


def write(lay, path, wf_id):
    sh_all = lay["shapes"]
    by_lane = {}
    for s in sh_all:
        if s["type"] in ("startEvent", "task", "parallelGateway", "endEvent"):
            by_lane.setdefault(s["lane"], []).append(s["id"])
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<bpmn:definitions {NS} id="Defs_{wf_id}" targetNamespace="https://openfn.org/workflow-review">',
         f'<bpmn:collaboration id="Collab_1"><bpmn:participant id="Pool_1" name={quoteattr(lay["pool"]["name"])} '
         f'processRef="Proc_1" /></bpmn:collaboration>',
         f'<bpmn:process id="Proc_1" isExecutable="false">', '<bpmn:laneSet id="LaneSet_1">']
    for i, ln in enumerate(lay["lanes"], 1):
        refs = "".join(f"<bpmn:flowNodeRef>{r}</bpmn:flowNodeRef>" for r in by_lane.get(ln["name"], []))
        x.append(f'<bpmn:lane id="Lane_{i}" name={quoteattr(ln["name"])}>{refs}</bpmn:lane>')
    x.append("</bpmn:laneSet>")
    inc = {s["id"]: [] for s in sh_all}
    out = {s["id"]: [] for s in sh_all}
    for f in lay["flows"]:
        out[f["source"]].append(f["id"])
        inc[f["target"]].append(f["id"])
    def io(sid):
        return "".join(f"<bpmn:incoming>{i}</bpmn:incoming>" for i in inc[sid]) + \
               "".join(f"<bpmn:outgoing>{o}</bpmn:outgoing>" for o in out[sid])
    for s in sh_all:
        name = quoteattr(s.get("label", ""))
        if s["type"] == "startEvent":
            ev = ('<bpmn:timerEventDefinition id="Timer_1" />' if s.get("trigger") == "cron"
                  else '<bpmn:messageEventDefinition id="Msg_1" />')
            x.append(f'<bpmn:startEvent id="{s["id"]}" name={name}>{io(s["id"])}{ev}</bpmn:startEvent>')
        elif s["type"] in ("task", "parallelGateway", "endEvent"):
            x.append(f'<bpmn:{s["type"]} id="{s["id"]}" name={name}>{io(s["id"])}</bpmn:{s["type"]}>')
        elif s["type"] == "dataObjectReference":
            x.append(f'<bpmn:dataObject id="DO_{s["id"]}" /><bpmn:dataObjectReference id="{s["id"]}" '
                     f'name={name} dataObjectRef="DO_{s["id"]}" />')
        elif s["type"] == "dataStoreReference":
            x.append(f'<bpmn:dataStoreReference id="{s["id"]}" name={name} />')
        elif s["type"] == "endpoint":
            x.append(f'<bpmn:textAnnotation id="{s["id"]}"><bpmn:text>{escape(s["label"])}</bpmn:text></bpmn:textAnnotation>')
    for n in lay["notes"]:
        x.append(f'<bpmn:textAnnotation id="{n["id"]}"><bpmn:text>{escape(chr(10).join(n["lines"]))}</bpmn:text></bpmn:textAnnotation>')
    for l in lay["legend"] + [lay["title"]]:
        x.append(f'<bpmn:textAnnotation id="{l["id"]}"><bpmn:text>{escape(l["label"])}</bpmn:text></bpmn:textAnnotation>')
    for f in lay["flows"]:
        nm = f' name={quoteattr(f["label"])}' if f["label"] else ""
        x.append(f'<bpmn:sequenceFlow id="{f["id"]}"{nm} sourceRef="{f["source"]}" targetRef="{f["target"]}" />')
    for a in lay["assocs"]:
        x.append(f'<bpmn:association id="{a["id"]}" sourceRef="{a["source"]}" targetRef="{a["target"]}" />')
    x.append("</bpmn:process>")
    # Diagram interchange (layout + colors)
    p = lay["pool"]
    x += ['<bpmndi:BPMNDiagram id="Diagram_1"><bpmndi:BPMNPlane id="Plane_1" bpmnElement="Collab_1">',
          f'<bpmndi:BPMNShape id="Pool_1_di" bpmnElement="Pool_1" isHorizontal="true">{bounds(p)}</bpmndi:BPMNShape>']
    for i, ln in enumerate(lay["lanes"], 1):
        x.append(f'<bpmndi:BPMNShape id="Lane_{i}_di" bpmnElement="Lane_{i}" isHorizontal="true">{bounds(ln)}</bpmndi:BPMNShape>')
    for s in sh_all + lay["notes"] + lay["legend"] + [lay["title"]]:
        lbl = label_bounds(s) if s["type"] in ("startEvent", "endEvent", "dataObjectReference", "dataStoreReference") else ""
        fill = s.get("fill") if s["type"] in ("task", "endEvent", "dataStoreReference") else None
        x.append(f'<bpmndi:BPMNShape id="{s["id"]}_di" bpmnElement="{s["id"]}"{color_attrs(fill)}>{bounds(s)}{lbl}</bpmndi:BPMNShape>')
    for f in lay["flows"]:
        pts = "".join(f'<di:waypoint x="{px:.0f}" y="{py:.0f}" />' for px, py in waypoints(lay, f))
        x.append(f'<bpmndi:BPMNEdge id="{f["id"]}_di" bpmnElement="{f["id"]}">{pts}</bpmndi:BPMNEdge>')
    for a in lay["assocs"]:
        pts = "".join(f'<di:waypoint x="{px:.0f}" y="{py:.0f}" />' for px, py in waypoints(lay, a, "assoc"))
        x.append(f'<bpmndi:BPMNEdge id="{a["id"]}_di" bpmnElement="{a["id"]}">{pts}</bpmndi:BPMNEdge>')
    x += ["</bpmndi:BPMNPlane></bpmndi:BPMNDiagram>", "</bpmn:definitions>"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(x) + "\n")
