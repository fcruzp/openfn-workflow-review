"""rwo setup: create or check the .env."""
from . import envfile
from .progress import emit


def run(root=".", create_only=False):
    status = envfile.check(root)
    if status is None:
        envfile.create(root)
        emit("\U0001f4dd I created the .env file in your folder. Open it with any text editor (Notepad works), "
             "fill in the three values, and save. When you're ready, type /revision-workflows-openfn again.")
        return 2
    missing = [k for k, ok in status.items() if not ok]
    if missing:
        emit("⚠ The .env file is missing: " + ", ".join(missing) +
             ". Fill them in, save, and type /revision-workflows-openfn again when you're ready.")
        return 2
    if create_only:
        emit("✔ The .env file already exists and is complete.")
    else:
        emit("✔ Settings OK (.env complete).")
    return 0
