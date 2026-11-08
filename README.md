# OpenFn Workflow Review

Review, improve, document, test-plan and diagram the workflows of an OpenFn (Lightning) project with Claude.

**Programs do everything mechanical; the model only does what needs judgment.** The `rwo` programs set up the project, download it with the OpenFn CLI, build the inventory, detect known problems, validate the model's work, and generate every deliverable (change guides, proposed code, test spreadsheet, Lucidchart diagrams and the final summary). It only **proposes**: it never changes, deploys or runs the project.

- How to use it: [docs/quickstart.md](docs/quickstart.md)
- How it is built: [ARCHITECTURE.md](ARCHITECTURE.md)
- Diagram style: [docs/bpmn-style-sheet.md](docs/bpmn-style-sheet.md)

## Status

Work in progress (v0.1). Available commands:

| Command | What it does |
|---|---|
| `python3 -m rwo setup` | Creates or checks the `.env` |
| `python3 -m rwo pull` | Downloads the project with the OpenFn CLI and detects changes |
| `python3 -m rwo inventory [--only "<workflow>"]` | Builds `review/inventory.md` and the work queue |
| `python3 -m rwo set env=yes` | Records the test-environment answer |
| `python3 -m rwo status` | Shows the progress |
| `node analyzer/analyze.js <step.js> [--adaptor <adaptor>]` | Runs the 12 automatic rules on one step (JSON output) |

Run them from the project folder, with this repo on `PYTHONPATH`.

Tests: `python3 -m unittest discover -s tests -v` (from the repo root).

## Requirements

Python 3.10+ (with PyYAML and openpyxl), Node.js 18+ and npm.
