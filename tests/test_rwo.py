"""Run with: python3 -m unittest discover -s tests -v   (from the repo root)"""
import os, shutil, subprocess, sys, tempfile, unittest, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from rwo import analyzer  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")
ALL_RULES = {f"R{n:02d}" for n in range(1, 13)}


def rwo(cwd, *args):
    env = dict(os.environ, PYTHONPATH=ROOT)
    return subprocess.run([sys.executable, "-m", "rwo", *args], cwd=cwd, env=env, capture_output=True, text=True)


class AnalyzerTests(unittest.TestCase):
    def test_bad_step_fires_every_rule(self):
        res = analyzer.analyze(os.path.join(FIX, "analyzer", "bad-step.js"), "@openfn/language-http@latest")
        self.assertIsNone(res["parse_error"])
        self.assertEqual({f["rule"] for f in res["findings"]}, ALL_RULES)

    def test_good_step_fires_nothing(self):
        res = analyzer.analyze(os.path.join(FIX, "analyzer", "good-step.js"), "@openfn/language-http@7.3.3")
        self.assertEqual(res["findings"], [])

    def test_findings_have_line_and_explanation(self):
        res = analyzer.analyze(os.path.join(FIX, "analyzer", "bad-step.js"))
        for f in res["findings"]:
            self.assertTrue(f["explain"] and f["fix"] and f["priority"])


class SetupAndInventoryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(FIX, "project"), self.dir, dirs_exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_setup_creates_env_and_gitignore(self):
        r = rwo(self.dir, "setup")
        self.assertEqual(r.returncode, 2)
        self.assertIn("OPENFN_API_KEY=", open(os.path.join(self.dir, ".env")).read())
        self.assertIn(".env", open(os.path.join(self.dir, ".gitignore")).read())

    def test_missing_values_are_named_never_shown(self):
        rwo(self.dir, "setup")
        r = rwo(self.dir, "inventory")
        self.assertEqual(r.returncode, 2)
        self.assertIn("OPENFN_API_KEY", r.stdout)

    def test_inventory_orders_steps_and_reads_credentials(self):
        with open(os.path.join(self.dir, ".env"), "w") as f:
            f.write("OPENFN_ENDPOINT=https://app.openfn.org\nOPENFN_PROJECT_ID=x\nOPENFN_API_KEY=secret-value\n")
        r = rwo(self.dir, "inventory")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("secret-value", r.stdout)
        state = json.load(open(os.path.join(self.dir, "review", "state.json")))
        steps = [s["name"] for s in state["workflows"][0]["steps"]]
        self.assertEqual(steps, ["Fetch records", "Send records"])
        self.assertIn("CREDENTIALS Source API test, Target API test", r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "review", "progress.md")))


if __name__ == "__main__":
    unittest.main()


class StepCycleTests(unittest.TestCase):
    """next -> submit (rejected / accepted) -> close-workflow -> questions."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(FIX, "project"), self.dir, dirs_exist_ok=True)
        with open(os.path.join(self.dir, ".env"), "w") as f:
            f.write("OPENFN_ENDPOINT=https://app.openfn.org\nOPENFN_PROJECT_ID=x\nOPENFN_API_KEY=k\n")
        rwo(self.dir, "inventory")
        rwo(self.dir, "set", "env=yes")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def answer(self, name, **over):
        good = open(os.path.join(FIX, "analyzer", "good-step.js")).read()
        a = {"workflow": "Sample sync", "step": name, "summary": "s", "priority": "no-change-needed",
             "automatic_findings": [], "findings": [], "proposed_code": good,
             "sandbox_tests": [{"name": "a", "input": {}, "expected_log": "x"},
                               {"name": "b", "input": {}, "expected_log": "y"}],
             "questions": [{"owner": "client", "text": f"{name}: question?"}]}
        a.update(over)
        p = os.path.join(self.dir, "review", "work", f"{name}.json")
        with open(p, "w") as f:
            json.dump(a, f)
        return os.path.relpath(p, self.dir)

    def test_full_cycle(self):
        self.assertIn("step 1/2", rwo(self.dir, "next").stdout)
        self.assertEqual(rwo(self.dir, "submit", self.answer("Fetch records")).returncode, 0)
        out = rwo(self.dir, "next").stdout
        self.assertIn("step 2/2", out)
        nxt = json.load(open(os.path.join(self.dir, "review", "work", "WF1-02-send-records.next.json")))
        ids = [f["id"] for f in nxt["automatic_findings"]]
        r = rwo(self.dir, "submit", self.answer("Send records"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("is not answered", r.stdout)
        code = "// [CHANGE] fixed\n" + open(os.path.join(FIX, "analyzer", "good-step.js")).read()
        r = rwo(self.dir, "submit", self.answer(
            "Send records", priority="blocking", proposed_code=code,
            automatic_findings=[{"id": i, "status": "confirmed", "reason": "r"} for i in ids],
            findings=[{"from": ",".join(ids), "priority": "blocking", "title": "t", "today": "d",
                       "change": "c", "fixed_in_code": False}]))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("WORKFLOW_NEXT WF1 -> run: rwo close-workflow WF1", rwo(self.dir, "next").stdout)
        self.assertEqual(rwo(self.dir, "close-workflow", "WF1").returncode, 0)
        prop = os.path.join(self.dir, "review", "sample-sync", "proposed")
        self.assertTrue(os.path.exists(os.path.join(prop, "CHANGES.md")))
        self.assertTrue(os.path.exists(os.path.join(prop, "sample-sync.yaml")))
        self.assertIn("2 questions", rwo(self.dir, "questions").stdout)

    def test_personal_data_is_rejected(self):
        rwo(self.dir, "next")
        r = rwo(self.dir, "submit", self.answer("Fetch records", summary="Calls 402-1234567-8"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("Personal data", r.stdout)


class DiagramTests(unittest.TestCase):
    """The Demo 3-shaped fixture must reproduce Demo 3's structure and colors."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(FIX, "diagram", "project"), self.dir, dirs_exist_ok=True)
        with open(os.path.join(self.dir, ".env"), "w") as f:
            f.write("OPENFN_ENDPOINT=https://app.openfn.org\nOPENFN_PROJECT_ID=x\nOPENFN_API_KEY=k\n")
        rwo(self.dir, "inventory")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_demo3_signature(self):
        import collections
        import xml.etree.ElementTree as ET
        r = rwo(self.dir, "diagram", "WF1", os.path.join(FIX, "diagram", "lanes.json"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = os.path.join(self.dir, "review", "contact-update", "diagram")
        self.assertTrue(os.path.getsize(os.path.join(out, "contact-update.png")) > 10000)
        tree = ET.parse(os.path.join(out, "contact-update.bpmn"))
        tags = collections.Counter(e.tag.split("}")[1] for e in tree.iter())
        expected = {"lane": 3, "startEvent": 1, "messageEventDefinition": 1, "task": 4, "parallelGateway": 1,
                    "endEvent": 3, "dataObjectReference": 1, "sequenceFlow": 7, "association": 2}
        self.assertEqual({k: tags[k] for k in expected}, expected)
        fills = collections.Counter()
        for e in tree.iter():
            for k, v in e.attrib.items():
                if k.endswith("}fill") or k == "fill":
                    fills[v.upper()] += 1
        self.assertEqual(fills["#E1E0FF"], 2)   # institutional API tasks
        self.assertEqual(fills["#FDD9A5"], 2)   # notification tasks
        self.assertEqual(fills["#C3F5C5"], 3)   # end events
        self.assertIn("DIAGRAM_PNG", r.stdout)

    def test_unknown_step_in_lanes_is_rejected(self):
        bad = json.load(open(os.path.join(FIX, "diagram", "lanes.json")))
        bad["steps"]["no-such-step"] = {"lane": "OpenFn Automation"}
        p = os.path.join(self.dir, "bad.json")
        json.dump(bad, open(p, "w"))
        r = rwo(self.dir, "diagram", "WF1", p)
        self.assertNotEqual(r.returncode, 0)


class TestsAndSummaryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(FIX, "project"), self.dir, dirs_exist_ok=True)
        with open(os.path.join(self.dir, ".env"), "w") as f:
            f.write("OPENFN_ENDPOINT=https://app.openfn.org\nOPENFN_PROJECT_ID=x\nOPENFN_API_KEY=k\n")
        rwo(self.dir, "inventory")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_spreadsheet_has_scenarios_and_institution_tabs(self):
        import openpyxl
        r = rwo(self.dir, "tests", "WF1", os.path.join(FIX, "scenarios.json"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wb = openpyxl.load_workbook(os.path.join(self.dir, "review", "tests", "test-scenarios.xlsx"))
        self.assertEqual(wb.sheetnames, ["Test scenarios", "Guide - Source API team", "Guide - Target API team"])
        self.assertEqual(wb["Test scenarios"]["A7"].value, "WF1-T03")
        g = wb["Guide - Target API team"]
        self.assertEqual(g["F5"].value, "Yes, with Source API team")
        self.assertEqual(g["F6"].value, "No")
        self.assertTrue(g["G5"].value.startswith("1. "))

    def test_bad_scenarios_are_rejected(self):
        bad = json.load(open(os.path.join(FIX, "scenarios.json")))
        bad["scenarios"][2]["institutions"] = ["Source API team"]
        bad["scenarios"][0]["setup"] += " Call 809-555-1234."
        p = os.path.join(self.dir, "bad.json")
        json.dump(bad, open(p, "w"))
        r = rwo(self.dir, "tests", "WF1", p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("credential tests need no institution", r.stdout)
        self.assertIn("Personal data", r.stdout)

    def test_summary_files(self):
        rwo(self.dir, "tests", "WF1", os.path.join(FIX, "scenarios.json"))
        r = rwo(self.dir, "summary")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SUMMARY_HTML review/SUMMARY.html", r.stdout)
        md = open(os.path.join(self.dir, "review", "SUMMARY.md"), encoding="utf-8").read()
        self.assertIn("2 not reviewed yet", md)
        self.assertIn("Source API team", md)
        page = open(os.path.join(self.dir, "review", "SUMMARY.html"), encoding="utf-8").read()
        self.assertNotIn("http://", page.replace("https://app.openfn.org", ""))
        self.assertIn("prefers-color-scheme:dark", page)
