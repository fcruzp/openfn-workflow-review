"""Entry point: python3 -m rwo <command> [options], run from the project folder."""
import argparse, sys, os
from . import setup, pull, inventory, queue, submit, workflow, questions, state as st
from .progress import emit


def main(argv=None):
    p = argparse.ArgumentParser(prog="rwo", description="OpenFn Workflow Review helpers")
    p.add_argument("--root", default=".", help="project folder (default: current folder)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="create or check the .env")
    sub.add_parser("create", help="create the .env only")
    pp = sub.add_parser("pull", help="download the project and detect changes")
    pp.add_argument("--force", action="store_true", help="download even if a review is unfinished")
    pi = sub.add_parser("inventory", help="build the inventory and the work queue")
    pi.add_argument("--only", help="exact name of the only workflow to review")
    ps = sub.add_parser("set", help="record an answer, for example env=yes or mode=checkpoint")
    ps.add_argument("pairs", nargs="+")
    sub.add_parser("status", help="show the progress")
    sub.add_parser("next", help="give the next step to review")
    psb = sub.add_parser("submit", help="validate a step answer and generate its guide")
    psb.add_argument("file")
    pc = sub.add_parser("close-workflow", help="complete the proposed workflow and CHANGES.md")
    pc.add_argument("key")
    sub.add_parser("questions", help="collect the questions for the client")
    a = p.parse_args(argv)
    root = os.path.abspath(a.root)

    if a.cmd in ("setup", "create"):
        sys.exit(setup.run(root, create_only=a.cmd == "create"))
    if setup.run(root, quiet=True) != 0:      # every other command needs a complete .env
        sys.exit(2)
    if a.cmd == "pull":
        sys.exit(pull.run(root, force=a.force))
    if a.cmd == "inventory":
        sys.exit(inventory.run(root, only=a.only))
    if a.cmd == "next":
        sys.exit(queue.run(root))
    if a.cmd == "submit":
        sys.exit(submit.run(root, a.file))
    if a.cmd == "close-workflow":
        sys.exit(workflow.close(root, a.key))
    if a.cmd == "questions":
        sys.exit(questions.run(root))
    if a.cmd == "set":
        s = st.load(root) or {}
        for pair in a.pairs:
            k, _, v = pair.partition("=")
            s[{"env": "env_answer"}.get(k, k)] = v
        st.save(s, root)
        emit("✔ Saved: " + ", ".join(a.pairs))
        sys.exit(0)
    if a.cmd == "status":
        s = st.load(root)
        if not s:
            emit("No review yet.")
            sys.exit(0)
        print(open(os.path.join(root, st.REVIEW_DIR, "progress.md"), encoding="utf-8").read())
        sys.exit(0)
