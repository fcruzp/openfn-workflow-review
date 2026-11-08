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
