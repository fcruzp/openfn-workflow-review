# OpenFn Workflow Review

Review, improve, document, test-plan and diagram the workflows of an OpenFn (Lightning) project with Claude.

**Programs do everything mechanical; the model only does what needs judgment.** The `rwo` programs set up the project, download it with the OpenFn CLI, build the inventory, detect known problems, validate the model's work, and generate every deliverable (change guides, proposed code, test spreadsheet, Lucidchart diagrams and the final summary). It only **proposes**: it never changes, deploys or runs the project.

- How to use it: [docs/quickstart.md](docs/quickstart.md)
- How it is built: [ARCHITECTURE.md](ARCHITECTURE.md)
- Diagram style: [docs/bpmn-style-sheet.md](docs/bpmn-style-sheet.md)

## Install (Cowork)

Install the plugin `dist/openfn-workflow-review.plugin` (built from `plugin/`). It contains the `/revision-workflows-openfn` skill and the whole tool in one file (`rwo.pyz`). Then follow [docs/quickstart.md](docs/quickstart.md).

## Commands

The skill runs these for you. Each one prints `PROGRESS` lines (shown to the user as is) and `TASK` lines (task-list updates).

| Command | What it does |
|---|---|
| `rwo create` / `rwo setup` | Creates or checks the `.env` (never shows the token) |
| `rwo pull [--force]` | Downloads the project with the OpenFn CLI and detects changes since the last review |
| `rwo inventory [--only "<workflow>"]` | Builds `review/inventory.md` and the work queue; archives the old deliverables of what changed |
| `rwo set env=yes` / `rwo set mode=checkpoint` | Records the answers |
| `rwo status` | Shows the progress |
| `rwo next` | Gives the next step to review (context, verified facts, automatic findings), or the next workflow command |
| `rwo submit <step.json>` | Validates the review of a step and writes its change guide and proposed code |
| `rwo close-workflow WF1` | Completes the proposed workflow and its `CHANGES.md` |
| `rwo diagram WF1 <lanes.json>` | Draws the diagram (`.bpmn` for Lucidchart + `.png`) in the OpenFn house style |
| `rwo tests WF1 <scenarios.json>` | Builds `review/tests/test-scenarios.xlsx` (scenarios + one guide tab per institution) |
| `rwo questions` | Collects the questions for the client in `review/questions.md` |
| `rwo summary` | Writes `review/SUMMARY.md` and `review/SUMMARY.html` |
| `rwo archive --all` | "Review everything again": archives the whole review (nothing is deleted) |

`rwo` is `python3 .rwo/rwo.pyz` in a project folder, or `python3 -m rwo` with this repo on `PYTHONPATH`. What the model writes (step, lanes and scenarios JSON) is documented in `rwo/schemas/`.

## Develop

- Tests: `python3 -m unittest discover -s tests -v`
- Build the tool and the plugin: `python3 scripts/build.py` (writes `dist/rwo.pyz` and `dist/openfn-workflow-review.plugin`, and refreshes `plugin/skills/revision-workflows-openfn/tool/` and `references/`)
- New analyzer rules: one file in `analyzer/rules/` plus a case in the fixtures.

## Requirements

Python 3.10+ and Node.js 18+ (both are in the Cowork workspace). Missing Python libraries (PyYAML, openpyxl, Pillow) and the OpenFn CLI are installed automatically.
