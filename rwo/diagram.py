"""rwo diagram: draw a workflow as .bpmn (for Lucidchart) and .png (preview) in the house style."""
import json, os
from . import state as st
from .inventory import load_workflow
from .workflow import find
from .diagram_layout import validate, build
from .diagram_bpmn import write as write_bpmn
from .diagram_png import render
from .progress import emit


def run(root, key, spec_path):
    state = st.load(root)
    wf = find(state, key)
    if not wf:
        emit(f"✖ Unknown workflow {key}.")
        return 1
    try:
        spec = json.load(open(os.path.join(root, spec_path), encoding="utf-8"))
    except Exception as e:
        emit(f"✖ The lanes file is not valid JSON: {e}")
        return 1
    wf_yaml = load_workflow(os.path.join(root, "workflows", wf["dir"]))
    errs = validate(spec, wf_yaml)
    if errs:
        print("REJECTED: fix these items in the lanes file and run rwo diagram again:")
        for e in errs:
            print(f"  - {e}")
        return 1
    lay = build(spec, wf_yaml)
    out = os.path.join(root, st.REVIEW_DIR, wf["dir"], "diagram")
    os.makedirs(out, exist_ok=True)
    bpmn, png = os.path.join(out, wf["dir"] + ".bpmn"), os.path.join(out, wf["dir"] + ".png")
    write_bpmn(lay, bpmn, wf["key"])
    render(lay, png)
    wf["diagram"] = True
    st.save(state, root)
    emit(f"✔ {wf['key']}: diagram ready (review/{wf['dir']}/diagram/: .bpmn for Lucidchart, .png preview).")
    print(f"DIAGRAM_PNG {os.path.relpath(png, root)}")
    return 0
