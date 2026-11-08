"""Bootstrap for rwo.pyz: unpack once to a cache folder, check the Python libraries, run the CLI."""
import hashlib, os, subprocess, sys, tempfile, zipfile

archive = os.path.dirname(os.path.abspath(__file__))
digest = hashlib.sha256(open(archive, "rb").read()).hexdigest()[:12]
cache = os.path.join(os.path.expanduser("~"), ".cache", "rwo", digest)
if not os.path.isdir(cache):
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    tmp = tempfile.mkdtemp(dir=os.path.dirname(cache))
    with zipfile.ZipFile(archive) as z:
        z.extractall(tmp)
    try:
        os.rename(tmp, cache)
    except OSError:     # another process unpacked it first
        pass
sys.path.insert(0, cache)

missing = []
for mod, pkg in (("yaml", "pyyaml"), ("openpyxl", "openpyxl"), ("PIL", "pillow")):
    try:
        __import__(mod)
    except ImportError:
        missing.append(pkg)
if missing:
    print("PROGRESS ▶ Installing Python libraries: " + ", ".join(missing), flush=True)
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "--break-system-packages", *missing],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("PROGRESS ✖ Could not install " + ", ".join(missing) + ". Install them with: pip install " + " ".join(missing))
        sys.exit(4)
    import site, importlib
    importlib.reload(site)

from rwo.cli import main  # noqa: E402
main()
