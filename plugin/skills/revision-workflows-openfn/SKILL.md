---
name: revision-workflows-openfn
description: "Reviews, improves, documents, test-plans and diagrams the workflows of an OpenFn (Lightning) project with the rwo tool, showing progress after every step. Use when the user types /revision-workflows-openfn, or asks for an OpenFn workflow code review, change guides, test scenarios, institution test guides or Lucidchart/BPMN workflow diagrams."
---

# OpenFn Workflow Review

A program called `rwo` does everything mechanical: setup, download, inventory, automatic code checks, validation, every file and every progress line. Your job is only the judgment: review each step, write the proposed code, the diagram content and the test scenarios as JSON, and hand them to `rwo`. Never write a deliverable by hand.

## Rules

1. **Relay progress as is.** After every `rwo` command, send each line that starts with `PROGRESS ` to the user, without the prefix and without rewording (use `SendUserMessage` or a similar verbatim tool if one exists). Apply each `TASK <action> | <name> | <description>` line with the task-list tool if one exists (create or update the task with that name). Send nothing else between steps: no code, no findings, they live in the files.
2. **Never stop to ask "shall I continue?".** Run the loop until `rwo` says everything is done (except in checkpoint mode, below).
3. **Propose, never apply.** Never edit `workflows/`, never deploy, never run the project's workflows. `rwo` writes everything under `review/`.
4. **Never invent.** Use the verified facts that `rwo next` gives you. Spend at most about 3 minutes verifying any one behavior; if it can't be confirmed, write an assumption and a question for the client.
5. **No secrets or personal data.** Never read, print or copy the `OPENFN_API_KEY` line of `.env`, never ask for a token. Invented test data only.
6. **English** in every deliverable, code comment and log message unless the user asks otherwise. Exact workflow and step names.

## 1. Get the tool ready (every run)

- **Project folder:** the folder the user connected for this review. Run every `rwo` command from that folder, with the shell that can see it (in Cowork, the shell on the user's computer).
- **Tool:** `tool/rwo.pyz` in this skill's folder (one file, version in `tool/VERSION`). It must be at `.rwo/rwo.pyz` inside the project folder. If it is missing, or `python3 .rwo/rwo.pyz --version` differs from `tool/VERSION`, copy it there. If the skill folder and the project folder are on different machines, transfer the file with the file tools you have (for example write it to your outputs folder, then commit it into the project folder). If nothing works, download it: `curl -fsSL -o .rwo/rwo.pyz https://github.com/fcruzp/openfn-workflow-review/releases/latest/download/rwo.pyz`.
- Below, `rwo` means `python3 .rwo/rwo.pyz`.

## 2. Commands

| The user types | Run |
|---|---|
| `/revision-workflows-openfn create` | `rwo create`, relay, stop. |
| `/revision-workflows-openfn` | The full run (section 3). |
| `/revision-workflows-openfn checkpoint` | `rwo set mode=checkpoint`, then the full run. |
| `/revision-workflows-openfn only "<name>"` | The full run, with `rwo inventory --only "<name>"`. If the name is unclear, list the workflows from `review/inventory.md` and ask. |
| "show the progress" | `rwo status` |
| "review everything again" | `rwo archive --all`, then `rwo pull --force`, then continue from step 3 of the full run. |

## 3. The full run

1. `rwo setup`. Exit code 2 → relay and stop (the user fills in `.env` and runs the command again).
2. `rwo pull`. Read its `NEXT` line:
   - `NEXT resume` → go to the loop (step 5).
   - `NEXT unchanged` → show `review/SUMMARY.html` again (step 7.3) and stop.
   - `NEXT -> run: rwo inventory` → step 3.
   - Exit code 3 (domain blocked) → relay, wait until the user says the download finished, then step 3.
3. `rwo inventory` (with `--only "<name>"` if asked).
4. **One question**, only on a new review: "Do all these credentials point to test environments? (<names from the `CREDENTIALS` line>)". Record it with `rwo set env=yes` or `rwo set env=no`.
5. **The loop:** run `rwo next` and act on its output:
   - `NEXT_FILE <path>` and `ANSWER_FILE <path>` → review the step (section 4), write the answer to `ANSWER_FILE`, run `rwo submit <ANSWER_FILE>`. If it prints `REJECTED`, fix exactly the listed items and submit again. Then `rwo next` again.
   - `WORKFLOW_NEXT WFn -> run: rwo close-workflow WFn` → run it, then `rwo next`.
   - `WORKFLOW_NEXT WFn -> run: rwo diagram WFn <lanes.json>` → write `review/work/WFn.lanes.json` (section 5), run `rwo diagram WFn review/work/WFn.lanes.json`, fix and rerun if rejected, then `rwo next`.
   - `WORKFLOW_NEXT WFn -> run: rwo tests WFn <scenarios.json>` → write `review/work/WFn.scenarios-draft.json` (section 6), run `rwo tests WFn review/work/WFn.scenarios-draft.json`, fix and rerun if rejected. **Checkpoint mode:** the workflow is now done; send a 3-line summary (steps, blocking items, files) and wait for `approved` or requested changes. Then `rwo next`.
   - `ALL_WORKFLOWS_DONE` → step 6.
6. `rwo questions`, then `rwo summary`.
7. Close:
   1. Relay the progress lines.
   2. Close in two or three lines: done, number of blocking items, where the files are.
   3. Show the file in the `SUMMARY_HTML` line in the session with the file-preview tool if one exists (for example `SendUserFile` with `display: "render"`, staging it first if it is on the user's computer); otherwise show `review/SUMMARY.md`.

The user can interrupt in plain words at any time; do what they ask, then resume the loop with `rwo next`.

## 4. Reviewing a step (the judgment)

Read the `NEXT_FILE` JSON: the step code with line numbers, what it receives and passes on, the verified adaptor facts and the automatic findings (A1, A2…) with rule, line, evidence and fix pattern. The exact answer format is in `references/step-json.md`.

- **Automatic findings:** confirm or discard each one, always with a one-sentence reason based on the code. Never skip one.
- **Your own findings:** check error handling (friendly log message for every error, throw when the step can't continue, per-item errors logged and skipped with a summary), **pagination** on every call that fetches a list (reading only the first page loses records: blocking; never assume field names, ask the client), values used without checking they exist, and what the next step expects.
- **Priorities:** blocking (breaks the flow, loses or duplicates data), fix-before-production, optional. `priority` is the highest one, or `no-change-needed`.
- **Proposed code:** the complete step code, every change marked `// [CHANGE] <why>`, patterns in `references/code-patterns.md`. Each step needs its own copy of a helper (steps don't share code). Keep the original code where nothing changes.
- **Sandbox tests:** 2 to 4 (normal, empty, failure), with invented input JSON and the expected log.
- **Assumptions and questions:** each one names the step and the behavior and can be understood on its own. Owner: `client`, `openfn` or the institution's name.
- If the adaptor version differs from the verified facts, check the adaptor source quickly (`npm pack @openfn/<adaptor>@<version>`), within the time box.

## 5. Diagram content (`lanes.json`)

Format in `references/lanes-json.md`. `rwo` draws everything in the OpenFn house style; you only give content:
- Lanes: the system that starts or feeds the flow on top, then the OpenFn lane, then the target systems, then "OpenFn Collections" if indicators are used. Real system names. Add a lane for any actor the user named as part of the process, even if it stays empty.
- `kind` per step: institutional (calls an institution's API), notification (SMS, WhatsApp, email), indicator, internal. The endpoint as `METHOD /path`.
- Notes: "[FC] Suggestions" (FC01…) with the main proposed changes, "@Client - Questions" (P1…) with the open questions, "Data used…" in the source lane. Short lines.

## 6. Test scenarios (`scenarios.json`)

Format in `references/scenarios-json.md`. Cover, where they apply: Normal flow, Edge data, Invalid data, System failure, Credentials, OpenFn behavior, Trigger, Security and operations. Infer the partner institutions from the systems the code calls; don't ask. Credential tests have no institution (the client edits the test credential in Lightning). For each institution: what to check, why (what could go wrong in production), and plain steps before, during and after the test.
