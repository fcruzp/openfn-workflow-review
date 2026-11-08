# scenarios.json: what the reviewer writes for each workflow's tests

Write one file per workflow, then run `rwo tests <WF key> <file>`. The program validates it, numbers the
scenarios (`WF1-T01`, `WF1-T02`…), works out the "Joint test?" column and rebuilds
`review/tests/test-scenarios.xlsx` with every workflow reviewed so far.

```json
{
  "workflow": "<exact workflow name>",
  "scenarios": [
    {
      "ref": "s1",
      "category": "Normal flow | Edge data | Invalid data | System failure | Credentials | OpenFn behavior | Trigger | Security and operations",
      "priority": "blocking | fix-before-production | optional",
      "step": "<exact step name, or null for the whole workflow>",
      "title": "What we test, in one line.",
      "setup": "How to prepare it in the sandbox, with invented test data.",
      "expected": "What must happen: run result, log message, data in each system.",
      "institutions": ["<institution that has to act>"],
      "notes": "Optional."
    }
  ],
  "institution_guides": [
    {
      "institution": "<name>",
      "intro": "Optional one-paragraph explanation for this institution.",
      "tests": [
        {
          "ref": "s1",
          "check": "What we want to check, in plain words.",
          "why": "Why we run this test (what could go wrong in production).",
          "before": ["Step 1", "Step 2"],
          "during": ["Step 1"],
          "after": ["Step 1"],
          "evidence": "Optional. Default: screenshot with the record ID, the date and the name of who checked.",
          "note": "Optional: conflicts with proposed changes or open questions."
        }
      ]
    }
  ]
}
```

## Rules checked by `rwo tests`

1. `workflow` and every `step` are exact names; `ref` values are unique.
2. Category and priority come from the lists above.
3. Credential tests have no institutions (the client edits the test credential in Lightning).
4. Every institution named in a scenario has a guide, and every guide test points to an existing `ref`.
5. `before`, `during` and `after` are lists of plain steps; the program numbers them.
6. No personal data: no real national IDs (use `000-0000000-0`) and no Dominican phone numbers (use `555-0100`).
