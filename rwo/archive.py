"""Archive old deliverables instead of deleting them: review/archive/<YYYY-MM-DD>/..."""
import os, shutil, datetime
from . import state as st


def folder(root):
    base = os.path.join(root, st.REVIEW_DIR, "archive", datetime.date.today().isoformat())
    d, k = base, 2
    while os.path.exists(d) and os.listdir(d) and getattr(folder, "_used", None) != d:
        d = f"{base}-{k}"
        k += 1
    folder._used = d
    return d


def move(root, rel_paths, dest=None):
    """Move each path (relative to root, under review/) into the archive, keeping its relative path."""
    dest = dest or folder(root)
    moved = []
    for rel in rel_paths:
        src = os.path.join(root, rel)
        if not os.path.exists(src):
            continue
        inner = os.path.relpath(src, os.path.join(root, st.REVIEW_DIR))
        target = os.path.join(dest, inner)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.exists(target):
            target += "-old"
        shutil.move(src, target)
        moved.append(inner)
    return dest, moved


def archive_all(root):
    """'Review everything again': move all of review/ (except archive/) into the archive."""
    rv = os.path.join(root, st.REVIEW_DIR)
    if not os.path.isdir(rv):
        return None, []
    items = [os.path.join(st.REVIEW_DIR, n) for n in sorted(os.listdir(rv)) if n != "archive"]
    folder._used = None
    return move(root, items)
