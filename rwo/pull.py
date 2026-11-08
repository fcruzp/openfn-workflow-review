"""rwo pull: download the project with the OpenFn CLI and detect changes since the last review."""
import os, subprocess, shutil, glob, datetime, time, urllib.request
from . import envfile, state as st
from .progress import emit

CLI_DIR = os.path.join(os.path.expanduser("~"), ".cache", "rwo-cli")
CLI_BIN = os.path.join(CLI_DIR, "node_modules", ".bin", "openfn")


def ensure_cli():
    if os.path.exists(CLI_BIN):
        return CLI_BIN
    emit("▶ Installing the OpenFn CLI (one time)…")
    os.makedirs(CLI_DIR, exist_ok=True)
    subprocess.run(["npm", "install", "--no-fund", "--no-audit", "--silent", "@openfn/cli"],
                   cwd=CLI_DIR, check=True, stdout=subprocess.DEVNULL)
    return CLI_BIN


def reachable(endpoint):
    """True if the endpoint answers with any HTTP status; False if the network blocks it."""
    try:
        urllib.request.urlopen(urllib.request.Request(endpoint, method="HEAD"), timeout=15)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def workflow_dirs(root="."):
    return sorted(d for d in glob.glob(os.path.join(root, "workflows", "*")) if os.path.isdir(d))


def hashes(root="."):
    """{workflow_dir_name: {file_name: sha256}} for every workflow yaml and step file."""
    out = {}
    for d in workflow_dirs(root):
        out[os.path.basename(d)] = {os.path.basename(f): st.sha256(f)
                                    for f in sorted(glob.glob(os.path.join(d, "*")))
                                    if f.endswith((".js", ".yaml", ".yml"))}
    return out


def do_pull(root, vals):
    cli = ensure_cli()
    env = dict(os.environ, NODE_USE_ENV_PROXY="1")
    cmd = [cli, "project", "pull", vals["OPENFN_PROJECT_ID"], "--alias", "review"]
    r = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
    out = (r.stdout + r.stderr)
    if r.returncode != 0 or "Command failed" in out:
        if "401" in out or "Unauthorized" in out:
            emit("✖ Lightning rejected the token. Check OPENFN_API_KEY in .env and run the command again.")
        elif "404" in out:
            emit("✖ Lightning could not find the project. Check OPENFN_PROJECT_ID in .env.")
        else:
            emit("✖ The project could not be downloaded. Details:\n" + "\n".join(out.strip().splitlines()[-5:]))
        return False
    return True


def run(root=".", force=False):
    vals = envfile.public_values(root)
    prev = st.load(root)
    if prev and not st.finished(prev) and not force:
        emit("▶ A previous review is not finished: resuming it without downloading again.")
        print("NEXT resume -> run: rwo next")
        return 0
    if not reachable(vals["OPENFN_ENDPOINT"]):
        emit(f"✖ The network does not allow {vals['OPENFN_ENDPOINT']} from this workspace.\n"
             "Run this in a terminal inside your folder, then tell me when it finished:\n"
             f"  openfn project pull {vals['OPENFN_PROJECT_ID']} --alias review\n"
             "(An administrator of your Claude organization can allow that domain so I can do it next time.)")
        return 3
    emit("▶ Downloading the project from Lightning…")
    t0 = time.time()
    if not do_pull(root, vals):
        return 1
    new = hashes(root)
    n_steps = sum(1 for files in new.values() for f in files if f.endswith(".js"))
    emit(f"✔ Project downloaded: {len(new)} workflows, {n_steps} step files ({round(time.time()-t0)} s).")
    if prev:
        old = prev.get("hashes", {})
        changes = diff(old, new)
        prev["pending_changes"] = changes
        st.save(prev, root)
        if not changes:
            emit("✔ Nothing changed since the previous review.")
            print("NEXT unchanged -> show review/SUMMARY.html again and stop")
            return 0
        emit("▶ Changes since the previous review:\n" + "\n".join(f"  • {c}" for c in changes))
    print("NEXT -> run: rwo inventory")
    return 0


def diff(old, new):
    out = []
    for wf in sorted(set(old) | set(new)):
        if wf not in old:
            out.append(f"new workflow: {wf}")
            continue
        if wf not in new:
            out.append(f"removed workflow: {wf}")
            continue
        for f in sorted(set(old[wf]) | set(new[wf])):
            if f not in old[wf]:
                out.append(f"new file: {wf}/{f}")
            elif f not in new[wf]:
                out.append(f"removed file: {wf}/{f}")
            elif old[wf][f] != new[wf][f]:
                out.append(f"edited: {wf}/{f}")
    return out
