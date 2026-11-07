"""Entry point: python3 -m rwo <command> [options], run from the project folder."""
import argparse, sys, os
from . import setup, pull, inventory, state as st
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
    a = p.parse_args(argv)
    root = os.path.abspath(a.root)

    if a.cmd in ("setup", "create"):
        sys.exit(setup.run(root, create_only=a.cmd == "create"))
    if setup.run(root) != 0:      # every other command needs a complete .env
        sys.exit(2)
    if a.cmd == "pull":
        sys.exit(pull.run(root, force=a.force))
    if a.cmd == "inventory":
        sys.exit(inventory.run(root, only=a.only))
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
