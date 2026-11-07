# OpenFn Workflow Review: architecture (validated)

## 1. Principle

**Programs do everything mechanical. The model only does what needs judgment.**

Everything that can be done the same way every time (setup, download, inventory, known-error detection, validation, document generation, diagrams, progress) is a program. The model reads code, decides, explains and proposes, and always hands its work to a program as structured data (JSON). The program validates it and turns it into the final files. That way the output is consistent, nothing is invented in the format, and progress is visible by design: every command is short and prints its own progress line.

## 2. Distribution: one GitHub repo, one plugin

- **GitHub repo** (source of truth, versioned, open to contributions): `openfn-workflow-review`, under Francisco's personal GitHub account for now (it can be moved to the OpenFn organization later).
- **Cowork plugin** built from the repo: it bundles the skill and the programs, and installs with one click from the organization's plugin marketplace. A new version of the plugin is published from each tagged release of the repo.

```
openfn-workflow-review/
├── README.md                     # quickstart (the current guide)
├── ARCHITECTURE.md               # this document
├── CHANGELOG.md
├── plugin/                       # Cowork plugin package
│   └── skills/revision-workflows-openfn/SKILL.md
├── rwo/                          # the programs (Python)
│   ├── cli.py                    # entry point: `rwo <command>`
│   ├── setup.py  pull.py  inventory.py  queue.py  submit.py
│   ├── tests_xlsx.py  diagram.py  summary.py  progress.py
│   ├── schemas/                  # JSON schemas for what the model writes
│   ├── templates/                # change guide, CHANGES.md, SUMMARY.md/.html
│   └── style/bpmn-style.json     # the validated diagram style (Demo 3)
├── analyzer/                     # code checks (Node, reads JavaScript exactly)
│   ├── analyze.js
│   └── rules/R01-…js  R02-…js …
└── tests/
    ├── fixtures/                 # small fake OpenFn projects with known problems
    └── golden/                   # expected outputs (for example the Demo 3 diagram)
```

**Languages:** Python 3 for orchestration and file generation (openpyxl for the spreadsheet, a small drawing library for the PNG). Node for the code analyzer, because it parses JavaScript exactly (with `acorn`). Both are already available in the Cowork workspace.

## 3. The run, command by command

| # | Command | Who | What it does | Output |
|---|---|---|---|---|
| 1 | `rwo setup` | program | Checks `.env`; creates it (and `.gitignore`) if missing. Never prints the token. | message: ok / what's missing |
| 2 | `rwo pull` | program | Pulls the project with the OpenFn CLI (`NODE_USE_ENV_PROXY=1`), hashes every step, detects changes against the previous review, archives what changed. | `workflows/`, hashes in `review/state.json` |
| 3 | `rwo inventory` | program | Reads every `workflow.yaml`: triggers, steps, edges, adaptors and versions, credential names, external systems. Builds the work queue. | `review/inventory.md`, `review/state.json` |
| — | *(question)* | model | Asks the user the one setup question (test environment) and records the answer with `rwo set env=test`. | |
| 4 | `rwo next` | program | Gives the next step to review: its code, what it receives and passes on, the adaptor facts that apply, and the **automatic findings** of the analyzer, with line numbers. Prints `▶ WF1 · step 3/7 …`. | JSON to the model |
| 5 | *(analysis)* | model | Reads the step, confirms or discards each automatic finding, adds its own, decides priorities, writes the proposed code, the sandbox tests and the questions. | `review/work/<step>.json` |
| 6 | `rwo submit <file>` | program | **Validates** (schema, exact names, `[CHANGE]` marks, `node --check`, no personal data patterns, every automatic finding answered). If something fails, it rejects with a clear list of what to fix. If it passes, it writes the change guide and the proposed `.js`, updates progress and prints `✔ … [██████░░] 6/21 · ~12 min left`. | guide `.md`, `proposed/<step>.js` |
| — | repeat 4-6 | | until the workflow has no pending steps | |
| 7 | `rwo close-workflow <wf>` | program | Completes `proposed/` (copy of `workflow.yaml` + one `.js` per step) and writes `CHANGES.md`. | `review/<wf>/proposed/` |
| 8 | `rwo diagram <wf> <lanes.json>` | program + model | The model only gives the lanes (systems and actors), the task labels and the notes. The program lays it out and draws it with the validated style, and writes both files from the same drawing. | `<wf>.bpmn`, `<wf>.png` |
| 9 | `rwo tests <wf> <scenarios.json>` | program + model | The model writes the scenarios as JSON; the program validates and builds the spreadsheet (one tab per institution, colors, columns). | `review/tests/test-scenarios.xlsx` |
| 10 | `rwo questions` | program | Collects every question from the submitted JSONs, groups them by owner, numbers them. | `review/questions.md` |
| 11 | `rwo summary` | program | Builds the final summary from the recorded data, and prints the path so the model opens it in the panel. | `SUMMARY.md`, `SUMMARY.html` |

Commands for the user stay the same: `/revision-workflows-openfn create`, `/revision-workflows-openfn`, `checkpoint` and `only "<workflow>"`. The skill just tells the model which `rwo` commands to run, in which order.

## 4. What the model writes (data contracts)

All are validated by JSON schemas in `rwo/schemas/`.

**`step.json`** (one per step)
```json
{
  "workflow": "<exact name>",
  "step": "<exact name>",
  "summary": "What this step does, in 2-3 sentences.",
  "findings": [
    {
      "rule": "R01",
      "status": "confirmed",
      "priority": "blocking",
      "today": "What happens today, in plain words.",
      "change": "What the proposal changes."
    },
    {
      "rule": null,
      "status": "new",
      "priority": "fix-before-production",
      "today": "…",
      "change": "…"
    }
  ],
  "proposed_code": "…full code with // [CHANGE] marks…",
  "behavior_table": [{"what_happens": "…", "run_result": "Failed", "log": "…"}],
  "sandbox_tests": [{"name": "Normal case", "input": {}, "expected_log": "…"}],
  "assumptions": ["…"],
  "questions": [{"owner": "client", "text": "…"}]
}
```
Each automatic finding must come back as `confirmed` or `discarded` (with a reason). The model can't skip one.

**`lanes.json`** (per workflow): the ordered lanes, which lane each step and end event belongs to, and the notes (suggestions, questions, data used, assumptions).

**`scenarios.json`** (per workflow): the scenarios and, for each institution, before / during / after / evidence.

## 5. The analyzer: automatic rules (first set)

Each rule has an ID, a default priority, a plain-language explanation and the fix pattern. The model confirms or discards; it never has to remember the rule.

| ID | Detects | Default priority |
|---|---|---|
| R01 | `post`/`put`/`patch` with the options as a function (headers silently dropped) | blocking |
| R02 | Use of `state.data` right after an `each(...)` as if it held the whole list | blocking |
| R03 | Calls to external systems without error handling (no `.catch` or friendly message) | fix before production |
| R04 | List fetch with paging signs (`page`, `limit`, `offset`, `next`, `cursor`, `total`) and no loop | blocking (if confirmed) |
| R05 | Personal data in URLs, query strings or `console.log` | fix before production |
| R06 | A value from another system used without checking it exists (token, ID, list) | fix before production |
| R07 | HTTP calls without `timeout` | optional |
| R08 | Hardcoded test values (fixed dates, phone numbers, IDs) | fix before production |
| R09 | Adaptor pinned to `@latest` instead of a fixed version | fix before production |
| R10 | Secrets or tokens written in the code | blocking |
| R11 | Bearer header built from a value that may be undefined | blocking |
| R12 | Per-item loop where one failure stops all the others | fix before production |

New rules are added as new files in `analyzer/rules/`, each with its own fixture test.

## 6. Diagram generation

- The validated style (`style/bpmn-style.json`, from Demo 3): layout, sizes, colors, lane order, annotation types, title and legend.
- The program builds the layout (lanes, left-to-right order from the workflow edges, branches for parallel steps, end events in the external systems' lanes) and writes the `.bpmn` (with layout and the colors it can carry) and the `.png` (all colors, legend and big title) from the same drawing.
- Golden test: generating Demo 3 from its data must reproduce the reference diagram.

## 7. Progress and live feedback

- `review/state.json` is the single source of progress (machine-readable); `review/progress.md` is generated from it for people.
- Every command prints one progress line. The skill's only rule about progress: **show each command's progress line to the user, as is**.
- Task list: `rwo inventory` prints the task list to create; `rwo next` and `rwo submit` print the task updates to apply.

## 8. Re-runs

Same behavior as today, now done by `rwo pull`: unfinished run → resume; finished and unchanged → say so and show the summary; changed → archive and review only what changed; "review everything again" → archive all and start fresh. Deliverables are never deleted.

## 9. Safety rules enforced by code

- `rwo` has no deploy command and never writes under `workflows/`.
- The token line of `.env` is never read into memory by `rwo` beyond checking it is not empty; the CLI reads it directly.
- `rwo submit` rejects personal-data patterns (national IDs, phone numbers) in guides and code.

## 10. Quality of the tool itself

- Unit tests per command and per rule, with small fake projects in `tests/fixtures/`.
- Golden tests for the guide template, the spreadsheet and the Demo 3 diagram.
- Continuous integration on GitHub runs the tests on every change.

## 11. Decisions

1. **Repo location:** Francisco's personal GitHub account for now.
2. **Name:** "OpenFn Workflow Review" (`openfn-workflow-review`) for the repo and the plugin. The skill keeps its command, `/revision-workflows-openfn`.
3. **Plugin marketplace:** to be decided later.
4. **Scope of the first version:** everything (all commands, rules, diagram, spreadsheet and summary).
