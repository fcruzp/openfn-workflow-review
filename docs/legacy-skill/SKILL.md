---
name: "revision-workflows-openfn"
description: "Review, improve, document, test-plan and diagram the workflows of an OpenFn (Lightning) project, step by step and verified against real adaptor code. Use for OpenFn workflow code reviews, change guides, test scenarios or workflow diagrams."
---

# OpenFn workflow review

## NON-NEGOTIABLE RULES (read first, re-read before every step)

1. **Show progress all the time.** Follow the STEP PROTOCOL below for every step: announce when it starts, announce when it ends. The user must never wait more than a few minutes without a visible update. A step is **not done** until its progress update has been sent.
2. **Time-box verification.** Spend at most about 3 minutes checking any single behavior. Reuse the verified facts in Appendix B. If something still can't be confirmed, write it down as an assumption and a client question, and move on.
3. **Propose, never apply.** Never edit `workflows/`, never run `openfn project deploy`, never run the project's workflows. All output goes under `review/`.
4. **Never invent.** Every claim is verified (Appendix B, the adaptor source, or a short local test) or clearly marked as an assumption.
5. **No secrets or personal data.** Never read, print or copy the `OPENFN_API_KEY` line; never ask for a token; use invented test data only.
6. **English** for all deliverables, code comments and log messages, unless the user explicitly asks for another language. Use the exact workflow and step names from the project.

## What it produces

For each workflow: a change guide per step with the complete proposed code, the complete proposed workflow, test scenarios plus one guide per partner institution, a Lucidchart diagram (`.bpmn` + `.png`), questions for the client, and a final visual summary shown in the session. It only proposes: the user tests the code in a Lightning sandbox and decides what to apply.

## Commands

| The user types | What you do |
|---|---|
| `/revision-workflows-openfn create` | Create `.env` and `.gitignore` (see Setup), tell the user what to fill in, stop. |
| `/revision-workflows-openfn` | **Full run.** Check `.env` (create it if missing, then stop). Ask the one setup question, then do **all** workflows **without stopping**. If a previous review exists, see "Running it again". |
| `/revision-workflows-openfn checkpoint` | Like the full run, but after each workflow show a short summary and wait for `approved`. |
| `/revision-workflows-openfn only "<workflow name>"` | Like the full run, but only that workflow (exact name; if unclear, list the workflows and ask). A later `/revision-workflows-openfn` continues with the rest. |

The user can interrupt in plain words at any time ("skip this workflow", "redo <step>", "show the progress", "review everything again"). Do it, then resume. Never ask "shall I continue?".

## STEP PROTOCOL (for every step, in this exact order)

**A. Start.** Mark the workflow's task as in progress (if not yet) and set its description to `step N/M: <step name>`. Send:
```
▶ WF1 · step 3/7 "<step name>" · reviewing…
```
**B. Review** the step (Phase 2), within the time box.
**C. Write** its change guide and save its proposed code (Phase 3).
**D. Update** `review/progress.md` (mark the step done, keep the code hash).
**E. Done.** Send:
```
[██████░░░░░░░░░░] 6/21 steps · ~12 min left
✔ WF1 · step 3/7 "<step name>": 1 blocking (pagination), 1 fix before production
```

**When a workflow ends** (after Phases 3b, 4 and 5): mark its task completed and send `✅ WF1 done: 7 guides, proposed workflow, tests, diagram · 2 blocking · starting WF2 (6 steps)`.

**How to send updates:** use a tool that shows the message verbatim if one exists (for example `SendUserMessage`); otherwise plain text. Use the task-list tool if one exists (for example `TaskCreate` / `TaskUpdate`). Never paste code or long findings into updates: they live in the files.

## Setup

Run with `create`, or automatically when a review command finds no `.env`. If `.env` exists, don't overwrite it: run the check in Phase 0 and say what's missing. Otherwise create `.env` with exactly:
```
# Fill in the three values after the = signs, save, then run /revision-workflows-openfn
# OPENFN_ENDPOINT: your Lightning address, for example https://app.openfn.org
# OPENFN_PROJECT_ID: the long code after /projects/ in the project's address in your browser
# OPENFN_API_KEY: your personal access token (Lightning user menu -> Personal Access Tokens). Never share it.
OPENFN_ENDPOINT=
OPENFN_PROJECT_ID=
OPENFN_API_KEY=
```
Create `.gitignore` with the line `.env` (or add the line). Then say: "I created the `.env` file in your folder. Open it with any text editor (Notepad works), fill in the three values, and save. When you're ready, type `/revision-workflows-openfn` again." Stop.

## Phase 0. Check, pull, ask

1. **Check `.env`** without showing the token:
   ```
   for k in OPENFN_ENDPOINT OPENFN_PROJECT_ID OPENFN_API_KEY; do grep -q "^$k=..*" .env && echo "$k ok" || echo "$k missing"; done
   ```
   Missing values: name them, ask the user to fill them in and run the command again, stop. You may read the endpoint and project ID lines.
2. **If `review/progress.md` exists:** go to "Running it again".
3. **Pull** (if `workflows/` is not there yet), using the OpenFn CLI in your shell on the user's computer:
   ```
   mkdir -p $HOME/cli && cd $HOME/cli && npm install --no-fund --no-audit @openfn/cli
   cd <project folder> && NODE_USE_ENV_PROXY=1 $HOME/cli/node_modules/.bin/openfn project pull <OPENFN_PROJECT_ID> --alias review
   ```
   `NODE_USE_ENV_PROXY=1` makes the CLI use the workspace's network proxy (without it, the CLI fails with `getaddrinfo` errors). A 401 means a wrong token: ask the user to check it in `.env`. If the domain is blocked by the network (proxy refusal), give the user the pull command to run in their own terminal, and mention once that an administrator of their Claude organization can allow the domain.
4. **Ask one question:** "Do all these credentials point to test environments? (credential names: …)"
5. **Create `review/progress.md`:** project, endpoint, pull date, environment answer, mode, start time, and a table `Workflow | Step | Code hash | Reviewed | Guide | Proposed code` (code hash = `sha256sum` of each step `.js`; also hash each `workflow.yaml`).
6. **Create the task list:** one task per workflow in scope (`WF1 · <name> · 7 steps`), plus "Questions for the client" and "Final summary". Send: `▶ Review started: 3 workflows, 16 steps · estimated ~25 min`.

## Running it again (when `review/progress.md` exists)

- **Unfinished run:** resume where it stopped, same mode, without pulling again.
- **Finished run:** pull again and compare code hashes. **Nothing changed:** say so in two lines, show the visual summary again, stop. **Something changed:** list what changed, move the affected old deliverables to `review/archive/<YYYY-MM-DD>/`, review only what changed (with the STEP PROTOCOL), and add "Changes since the previous review" to the summary.
- **"Review everything again":** move all of `review/` (except `archive/`) to `review/archive/<YYYY-MM-DD>/` and start fresh.
- Never delete deliverables: always archive.

## Phase 1. Inventory

For each workflow: trigger (cron in UTC or webhook), steps in order with exact names, edges and conditions, adaptor and credential name per step, external systems called, and what each step passes to the next. Save `review/inventory.md`. Send `✔ Inventory: 3 workflows, 16 steps`.

## Phase 2. Review a step

Write in plain words:
- **What this step does** (2-3 sentences; what it reads and writes).
- **What happens today**, verified, especially failure paths.
- **Priority** of each finding: **blocking** (breaks the flow, loses or duplicates data), **fix before production**, or **optional**.

Check every step against:
- **Errors:** friendly log message for every error; throw when the step can't continue (run ends Failed); for per-item errors, log and continue, then print a summary with the IDs to review; validate response shapes.
- **Pagination:** for every call that fetches a list, check whether the API pages results (`page`, `limit`, `offset`, `next`, `cursor`, `total`, `Link` header). Reading only the first page silently loses records: **blocking**. Never assume field names; if unknown, ask the client.
- **Known pitfalls:** see Appendix B.

## Phase 3. Change guide and proposed code

Write `review/<workflow folder>/wfN-stepX-<step-name>.md` with the template in Appendix C: complete proposed code with every change marked `// [CHANGE]` (syntax checked with `node --check`), how to test it in a sandbox, and assumptions/questions. Save the proposed code as `review/<workflow folder>/proposed/<same step file>.js`. Add any client questions to `review/questions.md`.

## Phase 3b. Complete proposed workflow

Make `review/<workflow folder>/proposed/` mirror `workflows/<workflow>/` (copy of `workflow.yaml` + one `.js` per step, original code where nothing changed) and write `CHANGES.md` (one line per step: priority + one-sentence change + link to its guide).

## Phase 4. Tests and institution guides

In `review/tests/test-scenarios.xlsx`: scenarios for each workflow (categories: Normal flow, Edge data, Invalid data, System failure, Credentials, OpenFn behavior, Trigger, Security and operations), and one guide tab per partner institution (columns in Appendix D). Infer the institutions from the external systems; don't ask. Wrong-credential tests need no institution (the client edits the test credential in Lightning). If the user gives an existing spreadsheet, work on a copy and check the existing sheets are unchanged.

## Phase 5. Diagram

OpenFn house style for Lucidchart (details in Appendix E): one pool, one horizontal lane per system, steps left to right in real order, colors by legend (purple = institutional APIs, orange = notification APIs, green = comments/questions), workflow name as large standalone text, nothing invented. Deliver `review/<workflow folder>/diagram/<name>.bpmn` (BPMN 2.0 XML with layout and colors) plus a `.png` preview. No draw.io or Mermaid.

## Phase 6. Questions for the client

Make sure `review/questions.md` is complete: grouped by owner (client team, each institution, OpenFn product); each question names the workflow and step, says what was observed and asks one concrete thing.

## Phase 7. Final summary (shown in the session)

1. Write `review/SUMMARY.md`: project, pull date, environment, total run time; table `Workflow | Steps | Blocking | Fix before production | Optional`; blocking items with links; assumptions; inferred institutions; where everything is; changes since the previous review (if any); what to do next (read the blocking guides, test in a sandbox, import each `.bpmn` into Lucidchart via File → Import → BPMN, upload the `.xlsx` to Drive and Save as Google Sheets, send the questions).
2. Build `review/SUMMARY.html`: one self-contained file (inline CSS, no external resources), readable in light and dark mode and on narrow screens; header; KPI tiles (workflows, steps, blocking, fix before production, optional); one card per workflow with a priority-mix bar and a step table with badges; highlighted blocking list with links; next steps as a checklist. Colors: blocking red, fix before production amber, optional blue-gray, no change green; every badge also shows its label in words.
3. **Show it in the session** with the file-preview tool if one exists (for example `SendUserFile` with `display: "render"`); otherwise show the `.md`.
4. Close in a few lines: done, number of blocking items, total time, summary open in the panel.

---

# APPENDICES (consult when needed)

## Appendix A. Reusable code patterns

Each step needs its own copy of a helper, because steps do not share code in OpenFn.

```js
// Translates a technical error into a friendly log message
const friendlyError = (system, action, e) => {
  const c = e.statusCode ?? e.status; // http adaptor: statusCode; Twilio: status
  if (c === 401 || c === 403) return `${system} rejected the credential while trying to ${action}. Check the step's credential.`;
  if (c === 404) return `${system} could not find the address while trying to ${action}. Check the credential's baseUrl.`;
  if (c >= 500) return `${system} had an internal error while trying to ${action} (code ${c}). Try again later or contact the ${system} team.`;
  if (c >= 400) return `${system} did not accept the request while trying to ${action} (code ${c}).`;
  if (e.code === 'UND_ERR_HEADERS_TIMEOUT' || e.code === 'UND_ERR_BODY_TIMEOUT')
    return `${system} did not respond in time while trying to ${action}. Check in ${system} whether the operation went through before retrying.`;
  if (e.code || e.cause?.code) return `Could not connect to ${system} while trying to ${action} (${e.code || e.cause.code}). Check the network or whether ${system} is available.`;
  return `Unexpected error while trying to ${action}: ${e.message}`;
};

// Single operation: friendly message, then stop
post('path', body, options).catch((e, state) => {
  throw new Error(friendlyError('SourceSystem', 'fetch the requests', e));
});

// Per-item operation inside each(): decide per error whether to continue or stop
const withTryCatch = op => async state => {
  const item = state.data;
  try {
    return await op(state);
  } catch (e) {
    if ([400, 409, 422].includes(e.statusCode)) { // affects only this item
      console.error(`Could not process ${item.id} (code ${e.statusCode}).`);
      return state; // continue with the next item
    }
    throw new Error(friendlyError('TargetSystem', `process ${item.id}`, e)); // affects everyone: stop
  }
};

// Pagination: fetch every page (adapt the field names to the API's documented paging rules)
fn(async state => {
  const all = [];
  const MAX_PAGES = 100; // safety cap
  let page = 1;
  while (page <= MAX_PAGES) {
    const { data } = await get('records', { query: { page, pageSize: 100 } })(state);
    const items = data.results ?? [];
    all.push(...items);
    if (!data.next || items.length === 0) break;
    page++;
  }
  console.log(`Fetched ${all.length} records in ${page} page(s)`);
  return { ...state, records: all };
});
```

## Appendix B. Verified facts (no need to re-test)

Verified for language-common 3.3.5, language-http 7.3.3 and OpenFn CLI 1.45.2. Re-verify only if the project uses different versions, by reading the adaptor source (`npm pack @openfn/language-http@<version>`).

- **`each` and `state.data`:** after `each(...)`, `state.data` holds only the last operation's response. Save lists in their own key before the `each`.
- **`post(path, data, options)`:** if `options` is a function, it is silently ignored, so the headers never go out (typical symptom: 401). Use `{ headers: state => ({ ... }) }`. `get(path, options)` does expand a function.
- **http errors:** status 400 or above throws an error with `statusCode`, `body` and `url`. The response body becomes `state.data`.
- **Operations inside `fn`:** `await get(path, options)(state)` returns the next state with the body in `.data` (makes pagination loops possible).
- **Auth:** Bearer from `access_token`, or Basic from username and password, only if `Authorization` is not already set.
- **Logs:** the adaptor logs the full URL with the query string: never put personal data in the query.
- **Timeout:** default 300000 ms; set `timeout` in the options. A timeout throws `UND_ERR_HEADERS_TIMEOUT` (no status code) and does not cancel the operation on the server.
- **`.catch((e, state) => ...)`** works on operations.
- **Twilio:** errors carry `.status` and `.code`; numbers must be E.164.
- **Lightning:** cron in UTC; a cron run starts from the final state of the last successful run (manual runs included); a run is Failed if a final step fails; credential values are scrubbed from logs.
- **CLI:** `openfn project pull <UUID> --alias <name>` creates `openfn.yaml`, `.projects/` and `workflows/`; it reads `OPENFN_API_KEY` and `OPENFN_ENDPOINT` from `.env`; in the Cowork workspace it needs `NODE_USE_ENV_PROXY=1`.

## Appendix C. Change guide template

```markdown
# <Workflow short name> · Change X · <exact step name>

**Status:** proposal (<date>). **Code reviewed:** pulled on <date>. **Credentials:** <as answered>.

| Item | Value |
|---|---|
| Workflow | <exact workflow name> |
| Step | <exact step name> |

**Priority:** <blocking / fix before production / optional / no change needed>

## What this step does
## What happens today
## How the change works
(Table: What happens | Run result (Success/Failed) | What the log says)
## Complete code
(Full proposed step code; every change marked `// [CHANGE]`.)
## How to test in a sandbox
(2-4 tests with test data: normal, empty, failure. Input JSON and expected log for each.)
## Assumptions and questions for the client
(Self-contained: each item names the step and the behavior.)
```

Never tell the reader to edit by line number: give the complete code.

## Appendix D. Institution guide tabs

One tab per partner institution, distinct tab color, a one-line title and a one-paragraph explanation only. Columns:

`ID | Workflow | Priority | What we want to check | Why we run this test | Joint test? | Before the test | During the test | After the test | What to send the client | Important note`

- **Why we run this test:** what could happen in production.
- **Joint test?:** "Yes" when another institution acts in the same test; agree on the same date and time.
- Numbered, concrete steps; evidence = screenshot with ID, date and name of who checked.
- Flag conflicts with proposed changes or open questions in "Important note".

## Appendix E. BPMN file contents

- a `collaboration` with one `participant` (the pool, named after the workflow);
- a `laneSet` with one `lane` per system;
- tasks, start and end events, gateways, and `textAnnotation` elements (linked with `association`) for comments and questions;
- layout: a `BPMNShape` with bounds for every element and a `BPMNEdge` with waypoints for every flow;
- colors with the bpmn.io color attributes (`bioc` / `color` namespaces);
- a legend drawn as filled colored boxes.

## Final checklist

- [ ] Progress updates sent at the start and end of every step; task list kept current; `progress.md` updated after every step
- [ ] Every behavior verified or marked as an assumption; no verification longer than ~3 minutes
- [ ] Change guide + proposed code for every step; complete proposed workflow with `CHANGES.md`
- [ ] Pagination checked on every list call
- [ ] Tests and institution guides in `review/tests/test-scenarios.xlsx`
- [ ] `.bpmn` + `.png` per workflow
- [ ] `review/questions.md` complete
- [ ] `SUMMARY.md` + `SUMMARY.html` written and shown in the session
- [ ] Nothing changed under `workflows/`, nothing deployed or run; old deliverables archived, never deleted
- [ ] No personal data, secrets or internal-tool references in client documents
