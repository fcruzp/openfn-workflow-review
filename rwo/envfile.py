"""Read and check the project's .env without ever exposing the token."""
import os, re

KEYS = ["OPENFN_ENDPOINT", "OPENFN_PROJECT_ID", "OPENFN_API_KEY"]
SECRET = "OPENFN_API_KEY"

TEMPLATE = """# Fill in the three values after the = signs, save, then run /revision-workflows-openfn
# OPENFN_ENDPOINT: your Lightning address, for example https://app.openfn.org
# OPENFN_PROJECT_ID: the long code after /projects/ in the project's address in your browser
# OPENFN_API_KEY: your personal access token (Lightning user menu -> Personal Access Tokens). Never share it.
OPENFN_ENDPOINT=
OPENFN_PROJECT_ID=
OPENFN_API_KEY=
"""


def path(root="."):
    return os.path.join(root, ".env")


def check(root="."):
    """Return {key: True/False} telling whether each value is filled. Never returns the secret."""
    result = {k: False for k in KEYS}
    p = path(root)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*([A-Z_]+)\s*=\s*(.*?)\s*$", line)
            if m and m.group(1) in result:
                result[m.group(1)] = bool(m.group(2).strip().strip('"').strip("'"))
    return result


def public_values(root="."):
    """Endpoint and project ID only (not secret)."""
    vals = {}
    with open(path(root), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*(OPENFN_ENDPOINT|OPENFN_PROJECT_ID)\s*=\s*(.*?)\s*$", line)
            if m:
                vals[m.group(1)] = m.group(2).strip().strip('"').strip("'").rstrip("/")
    return vals


def create(root="."):
    with open(path(root), "w", encoding="utf-8") as f:
        f.write(TEMPLATE)
    gi = os.path.join(root, ".gitignore")
    lines = open(gi, encoding="utf-8").read().splitlines() if os.path.exists(gi) else []
    missing = [x for x in (".env", ".rwo/") if x not in [l.strip() for l in lines]]
    if missing:
        with open(gi, "a", encoding="utf-8") as f:
            f.write(("\n" if lines and lines[-1] else "") + "\n".join(missing) + "\n")
