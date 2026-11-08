# OpenFn Workflow Review (Cowork plugin)

Reviews every workflow of an OpenFn (Lightning) project and produces, for each one: a change guide per step with the complete proposed code, the complete proposed workflow, test scenarios plus one guide per partner institution (`.xlsx`), a Lucidchart diagram (`.bpmn` + `.png`), questions for the client and a visual final summary.

It only **proposes**: it never changes your project in Lightning, never deploys and never runs workflows. Test the proposed code in a Lightning sandbox.

## How to use it

1. Connect an empty folder in Cowork.
2. Type `/revision-workflows-openfn create`, then fill in the `.env` file it creates (endpoint, project ID, personal access token).
3. Type `/revision-workflows-openfn`. Answer the one question. Claude reviews everything and shows progress after every step.

Options: `/revision-workflows-openfn checkpoint` (wait for `approved` after each workflow) and `/revision-workflows-openfn only "<workflow name>"`.

Full guide and source code: https://github.com/fcruzp/openfn-workflow-review

## Requirements

Python 3.10+ and Node.js 18+ where the folder is (both are in the Cowork workspace). The tool installs the OpenFn CLI and any missing Python library by itself.
