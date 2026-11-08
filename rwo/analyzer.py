"""Run the Node analyzer on one step file and return its automatic findings."""
import json, os, subprocess

ANALYZER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analyzer", "analyze.js")


def analyze(step_file, adaptor=""):
    cmd = ["node", ANALYZER, step_file] + (["--adaptor", adaptor] if adaptor else [])
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)
