# OpenFn Workflow Review

A Claude (Cowork) plugin that reviews every workflow of an OpenFn Lightning project and hands back everything a team needs before going to production: proposed code with a change guide per step, a test plan per partner institution, Lucidchart-ready diagrams in the OpenFn house style, questions for the client and a visual summary for managers and developers.

It only **proposes**. It never changes, deploys or runs anything in Lightning: you test the proposed code in a sandbox and decide what to apply.

- **Step-by-step guide:** [docs/quickstart.md](docs/quickstart.md)
- **How it is built:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Diagram house style:** [docs/bpmn-style-sheet.md](docs/bpmn-style-sheet.md)

## Install

In Cowork, type:

```
Install the plugin from https://github.com/fcruzp/openfn-workflow-review
```

Claude downloads the plugin file and shows you a card: press its button to install it.

The installable plugin file is always the `openfn-workflow-review.plugin` asset of the latest release: https://github.com/fcruzp/openfn-workflow-review/releases/latest/download/openfn-workflow-review.plugin (you can also download it and open it in Cowork yourself).

---

## Where it came from

This started in the Dominican Republic, on the **Servicios Proactivos** project with the Ministry of Public Administration (MAP). The project connects several government institutions through OpenFn workflows: one system detects an event, OpenFn moves the data to another institution, and the citizen is notified by SMS or WhatsApp.

Before going live, every workflow needed the same careful work:

- read each step's code and find what could break in production (lost records, missing error handling, values used without checking them, data that only reads the first page of a list);
- write the improved code and explain every change so the team could review it;
- prepare test guides that each institution could follow on its own (what to do before, during and after each test, and what evidence to send back);
- draw each workflow in Lucidchart following OpenFn's diagram standard;
- collect the open questions for the client.

Doing this by hand for every workflow took days, and it had to be redone every time the code changed.

## The idea

Use Claude for that review, but make it **repeatable and transportable**: something any OpenFn colleague could run on their own project with two commands, without being a developer and without touching the project in Lightning.

## First approach: a skill (a long set of instructions)

The first version was a Claude skill: a detailed set of instructions telling the model how to download the project with the OpenFn CLI, review each step, write the guides, build the spreadsheet and draw the diagrams.

It worked, and the reviews were useful, but testing it on a real project showed its limits:

- **No visible progress.** A project with 3 workflows of 6-7 steps took almost half an hour, and the user could go several minutes without knowing what was happening, even though the instructions asked for updates after every step.
- **Inconsistent output.** The same instructions produced slightly different file layouts from one run to the next.
- **Invented rules.** The diagrams looked close to the house style, but the model made up its own details (colors, positions, elements).
- **Too much to remember.** The longer the instructions got, the less reliably every rule was followed.

The lesson: a language model is excellent at judgment (reading code, deciding what matters, explaining it) but not a reliable executor of long mechanical checklists.

## The approach that worked: programs do the mechanical work, Claude does the judgment

The work was split in two:

- **Programs** do everything that must be done the same way every time: create the settings file, download the project, build the inventory, detect known problems in the code, validate what the model writes, generate every file, draw the diagrams and print the progress.
- **Claude** only does what needs judgment: confirm or discard each problem the programs found, find new ones, write the proposed code, the diagram content, the test scenarios and the questions.

Claude never writes a deliverable directly. It hands its work to the programs as structured data, and the programs **validate it** before turning it into files. If something is wrong (a step name that doesn't exist, a detected problem left unanswered, code that doesn't compile, a real phone number in the test data), the work is rejected with a list of what to fix, and Claude fixes it.

Progress is visible by design: every command prints its own progress line (for example `▶ WF1 · step 3/7 "Get users" · reviewing…` and `[██████░░░░] 6/21 steps · ~12 min left`), and Claude shows those lines as they are.

### What we achieved

- **Consistent deliverables:** same structure, same names, same diagram style on every run.
- **Live feedback:** the user sees each step start and finish, with a progress bar and the time left.
- **Nothing invented:** the diagram layout follows the OpenFn style exactly, the facts about the adaptors were checked against their source code, and anything that can't be verified is written down as an assumption or a question.
- **Re-runs that make sense:** if the project changes, only what changed is reviewed again. Old deliverables are archived, never deleted.
- **Safe by design:** the tool has no deploy command, never writes into the downloaded project and never reads the API token.

## From skill to plugin

The skill and the programs were then packaged together as a **Cowork plugin**. Installing it adds the `/revision-workflows-openfn` command, and the review tool travels inside it as a single file, so colleagues don't need to install anything else or clone this repo.

---

## How it works

You connect an empty folder in Cowork and type two commands:

| You type | What happens |
|---|---|
| `/revision-workflows-openfn create` | Claude creates a `.env` settings file in your folder. You fill in the Lightning address, the project ID and your personal access token. |
| `/revision-workflows-openfn` | Claude downloads the project with the OpenFn CLI, asks one question (do the credentials point to test environments?) and reviews every workflow without stopping, showing progress after every step. |

Options: `checkpoint` (Claude waits for your `approved` after each workflow) and `only "<workflow name>"` (review a single workflow). Full instructions, including what to do if your Lightning instance can't be reached, are in the [guide](docs/quickstart.md).

### The run, step by step

1. **Setup and download.** The settings are checked (the token is never shown) and the project is pulled from Lightning.
2. **Inventory.** Every workflow is read: trigger, steps in order, connections between steps, adaptors and credentials.
3. **Step-by-step review.** For each step, the programs give Claude the code, what the step receives and passes on, the verified adaptor facts and the problems found automatically. Claude reviews it and writes its answer; the programs validate it and generate the change guide and the proposed code.
4. **Per workflow.** The complete proposed workflow, its diagram (`.bpmn` for Lucidchart and a `.png` preview) and its test scenarios.
5. **Closing.** The questions for the client and the final summary, opened for the user.

### What you get

| Deliverable | Where |
|---|---|
| Visual summary (managers and developers), with links to everything below | `review/SUMMARY.html` (also `SUMMARY.md`) |
| Change guide per step: what it does, what happens today, the complete proposed code with every change marked, how to test it in a sandbox | `review/<workflow>/` |
| Complete proposed workflow (`workflow.yaml`, one file per step, `CHANGES.md`) | `review/<workflow>/proposed/` |
| Diagram for Lucidchart (`.bpmn`) and preview (`.png`) in the OpenFn house style | `review/<workflow>/diagram/` |
| Test scenarios plus one guide tab per partner institution | `review/tests/test-scenarios.xlsx` |
| Questions for the client, grouped by owner and ready for email | `review/questions.md` |

### Problems detected automatically

A code analyzer checks every step against these rules. Claude must confirm or discard each finding, with a reason; it can't skip one.

| Rule | Detects | Default priority |
|---|---|---|
| R01 | `post`/`put`/`patch` options written as a function (the headers are silently dropped) | Blocking |
| R02 | `state.data` used after `each(...)` as if it held the whole list | Blocking |
| R03 | Calls to external systems without error handling | Fix before production |
| R04 | Lists fetched with paging signs but no loop (only the first page is read) | Blocking |
| R05 | Personal data in URLs, query strings or logs | Fix before production |
| R06 | Values from another system used without checking they exist | Fix before production |
| R07 | HTTP calls without a timeout | Optional |
| R08 | Hardcoded test values (fixed dates, phone numbers, IDs) | Fix before production |
| R09 | Adaptor pinned to `@latest` | Fix before production |
| R10 | Secrets or tokens written in the code | Blocking |
| R11 | Bearer header built from a value that may be missing | Blocking |
| R12 | Per-item loops where one failure stops all the others | Fix before production |

### Safety rules

- Proposes only: no deploy, no changes to the project in Lightning, no workflow runs.
- The API token stays in `.env` (excluded from Git); it is never read, shown or sent anywhere.
- Test data must be invented: the validation rejects real national ID and phone number patterns.
- Previous deliverables are archived, never deleted.

## Requirements

The Claude desktop app with Cowork, and access to a Lightning project (address, project ID and a personal access token). Everything else (the OpenFn CLI and the libraries the tool needs) is installed automatically in the Cowork workspace.

If your Lightning instance is self-hosted and the workspace's network doesn't allow it, the guide explains the two options: ask an administrator to allow the domain, or download the project yourself with one CLI command.

## Repository contents

| Folder | What it holds |
|---|---|
| `plugin/` | The Cowork plugin: the `/revision-workflows-openfn` skill and the bundled tool |
| `rwo/` | The review programs (setup, download, inventory, validation, guides, diagrams, spreadsheet, summary) |
| `analyzer/` | The code analyzer and its 12 rules |
| `tests/` | Automated tests with small sample projects |
| `docs/` | The step-by-step guide, the diagram style sheet and the previous instructions-only skill, kept for reference |

## Contributing

Ideas, new analyzer rules and fixes are welcome. See [ARCHITECTURE.md](ARCHITECTURE.md) for the design; each new rule needs a sample case in `tests/`. The build script in `scripts/` produces the installable plugin.

## Author

Francisco Cruz (OpenFn), with Claude.
