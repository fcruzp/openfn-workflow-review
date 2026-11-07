"""Progress lines that every command prints, so the user always sees where the run is."""
import time

BAR_WIDTH = 16


def now():
    return time.time()


def bar(done, total, width=BAR_WIDTH):
    total = max(total, 1)
    filled = round(width * done / total)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def eta(state):
    """Estimate minutes left from the average time per finished step."""
    durations, pending = [], 0
    for wf in state.get("workflows", []):
        for st in wf["steps"]:
            if not st.get("in_scope", True):
                continue
            if st.get("status") == "done" and st.get("started_at") and st.get("done_at"):
                durations.append(st["done_at"] - st["started_at"])
            elif st.get("status") != "done":
                pending += 1
    if not durations:
        return None
    return round(sum(durations) / len(durations) * pending / 60)


def counts(state):
    done = total = 0
    for wf in state.get("workflows", []):
        for st in wf["steps"]:
            if not st.get("in_scope", True):
                continue
            total += 1
            done += st.get("status") == "done"
    return done, total


def line(state, text):
    done, total = counts(state)
    left = eta(state)
    tail = f" · ~{left} min left" if left is not None else ""
    return f"{bar(done, total)} {done}/{total} steps{tail}\n{text}"


def emit(text):
    """Every line meant for the user starts with PROGRESS so the skill can relay it as is."""
    for l in text.splitlines():
        print(f"PROGRESS {l}")


def task(action, name, description=""):
    """Instructions for the task-list tool, relayed by the model."""
    print(f"TASK {action} | {name} | {description}")
