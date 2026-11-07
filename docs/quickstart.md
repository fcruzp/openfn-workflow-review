# OpenFn Workflow Review: step-by-step guide

This guide walks you through reviewing, improving, documenting and diagramming the workflows of an OpenFn project with Claude and the `revision-workflows-openfn` skill. You don't need to be a developer or use a terminal: Claude downloads the project with the OpenFn CLI for you. You type two commands and answer one question.

**What the skill does:** it reviews the project and **proposes** improved code (step by step and for the whole workflow) with the documentation of every change. It never changes your project in Lightning and never runs it: you test the proposed code in a Lightning sandbox and decide what to apply.

> **Safety rules, always:**
> - Test the proposed code in a **Lightning sandbox**, never directly in the client's production project.
> - Use **invented test data** only: no real names, IDs or phone numbers.
> - **Never share your token** with anyone, and never paste it into the chat: it only goes in the `.env` file, which Claude never reads.

---

## Part A. One-time setup (about 5 minutes)

### 1. Install Claude and the skill

1. Install the Claude desktop app and sign in with your OpenFn account.
2. Open **Cowork** in the app.
3. Make sure the `revision-workflows-openfn` skill is enabled for your account (Settings → Skills).

### 2. Create an empty folder and connect it to Cowork

1. Create an **empty** folder, for example `C:\PROJECTS\<PROJECT_NAME>` on Windows or `~/Projects/<PROJECT_NAME>` on Mac.
2. In the Claude desktop app, in Cowork, click **Add folder** and choose it.

You don't need to create anything inside it.

---

## Part B. Review a project

### 3. Create the settings file

In Cowork, type:
```
/revision-workflows-openfn create
```
Claude creates a file named `.env` in your folder (and a `.gitignore`, so the file is never uploaded to Git). Nothing else happens yet.

> If you forget `create` and type just `/revision-workflows-openfn`, it's fine: Claude sees there is no `.env`, creates it the same way, and asks you to fill it in.

### 4. Fill in the settings file

Open `.env` in your folder with any text editor (Notepad works) and fill in the three values after the `=` signs:

| Value | Where to find it |
|---|---|
| `OPENFN_ENDPOINT` | Your Lightning address, for example `https://app.openfn.org` |
| `OPENFN_PROJECT_ID` | Open the project in Lightning and copy the long code after `/projects/` in the browser's address bar: `https://app.openfn.org/projects/`**`<PROJECT_ID>`**`/w` |
| `OPENFN_API_KEY` | Your personal access token: in Lightning, open your user menu (top right) → **Personal Access Tokens** → create one and copy it. You only see it once. |

Save the file. Never paste the token into the chat: Claude never reads it.

### 5. Start the review

Type:
```
/revision-workflows-openfn
```
Claude checks the `.env` first. If a value is missing, it tells you which one: fill it in, save, and when you're ready, type the command again.

If everything is there, Claude downloads the project and asks you **one** question: whether the project's credentials point to **test environments**. After your answer, it reviews **every workflow, from start to finish, without stopping**, and produces all the deliverables.

> **Prefer to check each workflow before Claude moves on?** Type this instead:
> ```
> /revision-workflows-openfn checkpoint
> ```
> It does the same, but when it finishes each workflow it shows you a short summary and waits for you to reply **`approved`** (or to ask for changes) before starting the next one.
>
> **Only want one workflow?** Type:
> ```
> /revision-workflows-openfn only "<EXACT_WORKFLOW_NAME>"
> ```
> Claude reviews just that workflow. Later, `/revision-workflows-openfn` continues with the others.
>
> **Session interrupted?** Type the same command again: Claude saves its progress in `review/progress.md` and picks up where it stopped.
>
> **Running it again after a finished review?** Claude downloads the project again and compares it with what it reviewed. If nothing changed, it just tells you so. If something changed, it reviews only what changed and keeps the previous deliverables in `review/archive/`. To redo everything from scratch, tell Claude "review everything again".

### 6. Read the summary

When the review is done, Claude opens the summary for you in the side panel, as a visual report with colors (it is also saved as `review/SUMMARY.html` and `review/SUMMARY.md`). It tells you:

- how many issues each workflow has, by priority (blocking, fix before production, optional);
- the blocking items, with a link to each change guide;
- the assumptions Claude could not verify;
- the partner institutions it found in the code (correct them if needed);
- where every deliverable is, and what to do next.

### 7. Test the proposed code in a sandbox

Each workflow has its complete proposed version in `review/<workflow>/proposed/` (one `workflow.yaml`, one `.js` per step, and a `CHANGES.md` that summarizes the changes). Try it in a **Lightning sandbox** before applying anything to the real project. Each change guide has a "How to test in a sandbox" section with test inputs and the expected log.

### 8. Import the diagram into Lucidchart

Each workflow has a `.bpmn` file (for Lucid) and a `.png` preview in `review/<workflow>/diagram/`.

1. Open Lucidchart and create a new document.
2. Go to **File → Import**, choose **BPMN**, and select the `.bpmn` file. Menu names can vary slightly.
3. Check it against the `.png` preview: lanes, steps, arrows and colors.

### 9. Share the test scenarios and institution guides as a Google Sheet

1. Upload `review/tests/test-scenarios.xlsx` to the Google Drive folder you share with the client.
2. Open it and choose **File → Save as Google Sheets**.

### 10. Send the questions to the client

Open `review/questions.md`: the open questions are grouped by owner and ready to paste into an email.

---

## If Claude can't reach your Lightning instance

Claude runs the OpenFn CLI inside Cowork, and Cowork only reaches the internet domains your organization allows. `app.openfn.org` works; a self-hosted instance (for example a government one) may be blocked. When that happens, Claude tells you, and you have two options:

- **Ask an administrator** of your organization's Claude account to allow that domain in the network settings. After that, Claude can download the project itself.
- **Download the project yourself**, once:
  1. Install Node.js (LTS, 18 or newer) from https://nodejs.org.
  2. In a terminal (PowerShell on Windows, Terminal on Mac):
     ```
     npm install -g @openfn/cli
     cd <PATH_TO_YOUR_FOLDER>
     ```
  3. Run the command Claude gives you:
     ```
     openfn project pull <PROJECT_ID> --alias review
     ```
  4. Tell Claude when it finished.

---

## What you end up with

| Deliverable | Format | Where |
|---|---|---|
| Final summary | `.html` (visual) and `.md` | `review/SUMMARY.html`, `review/SUMMARY.md` |
| Progress file | `.md` | `review/progress.md` |
| Change guide per step | `.md` | `review/<workflow>/wfN-stepX-<step>.md` |
| Proposed code per step and complete proposed workflow | `.js`, `workflow.yaml`, `CHANGES.md` | `review/<workflow>/proposed/` (your downloaded project in `workflows/` is never changed) |
| Test scenarios and institution guides | `.xlsx` (one tab per institution) | `review/tests/test-scenarios.xlsx` |
| Diagram | `.bpmn` and `.png` | `review/<workflow>/diagram/` (and imported into Lucidchart) |
| Questions for the client | `.md` | `review/questions.md`, ready for email |
