"""Build dist/rwo.pyz (the whole tool in one file) and dist/openfn-workflow-review.plugin.

Usage (from the repo root): python3 scripts/build.py
"""
import os, re, shutil, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
PLUGIN = os.path.join(ROOT, "plugin")
SKILL = os.path.join(PLUGIN, "skills", "revision-workflows-openfn")
SKIP = ("__pycache__", ".pyc")


def version():
    return re.search(r'__version__\s*=\s*"([^"]+)"', open(os.path.join(ROOT, "rwo", "__init__.py")).read()).group(1)


def add_tree(z, folder, arc_base):
    for dp, dns, fns in os.walk(folder):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in sorted(fns):
            if fn.endswith(SKIP):
                continue
            full = os.path.join(dp, fn)
            z.write(full, os.path.join(arc_base, os.path.relpath(full, folder)))


def build_pyz(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(ROOT, "scripts", "pyz_main.py"), "__main__.py")
        add_tree(z, os.path.join(ROOT, "rwo"), "rwo")
        add_tree(z, os.path.join(ROOT, "analyzer"), "analyzer")


def main():
    v = version()
    os.makedirs(DIST, exist_ok=True)
    pyz = os.path.join(DIST, "rwo.pyz")
    build_pyz(pyz)
    tool = os.path.join(SKILL, "tool")
    os.makedirs(tool, exist_ok=True)
    shutil.copy(pyz, os.path.join(tool, "rwo.pyz"))
    with open(os.path.join(tool, "VERSION"), "w") as f:
        f.write(v + "\n")
    refs = os.path.join(SKILL, "references")
    os.makedirs(refs, exist_ok=True)
    for name in ("step", "lanes", "scenarios"):
        shutil.copy(os.path.join(ROOT, "rwo", "schemas", f"{name}.schema.md"), os.path.join(refs, f"{name}-json.md"))
    manifest = os.path.join(PLUGIN, ".claude-plugin", "plugin.json")
    txt = open(manifest).read()
    open(manifest, "w").write(re.sub(r'"version":\s*"[^"]+"', f'"version": "{v}"', txt))
    out = os.path.join(DIST, "openfn-workflow-review.plugin")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        add_tree(z, PLUGIN, "")
    print(f"Built rwo {v}: {os.path.relpath(pyz, ROOT)} ({os.path.getsize(pyz)//1024} KB), "
          f"{os.path.relpath(out, ROOT)} ({os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
