# step.json: what the reviewer writes for each step

Write it to the path given in `ANSWER_FILE`, then run `rwo submit <that path>`. `rwo submit` rejects the file, with a list of what to fix, if any rule below is broken.

```json
{
  "workflow": "<exact workflow name, as in the .next.json>",
  "step": "<exact step name, as in the .next.json>",
  "summary": "What this step does, in 2-3 plain sentences (what it reads, what it writes).",
  "priority": "blocking | fix-before-production | optional | no-change-needed",
  "automatic_findings": [
    {"id": "A1", "status": "confirmed", "reason": "Why it applies here (one sentence)."},
    {"id": "A2", "status": "discarded", "reason": "Why it does not apply here (required)."}
  ],
  "findings": [
    {
      "from": "A1 | A3,A4 | new",
      "priority": "blocking | fix-before-production | optional",
      "title": "Short title",
      "today": "What happens today, verified, in plain words.",
      "change": "What the proposed code changes.",
      "fixed_in_code": true
    }
  ],
  "proposed_code": "The complete proposed step code. Every change marked with a // [CHANGE] comment.",
  "behavior": [
    {"what_happens": "The system rejects the credential", "run_result": "Failed", "log": "Friendly message shown"}
  ],
  "sandbox_tests": [
    {"name": "Normal case", "input": {}, "expected_log": "..."},
    {"name": "Failure case", "input": {}, "expected_log": "..."}
  ],
  "assumptions": ["Things that could not be verified."],
  "questions": [
    {"owner": "client | openfn | <institution name>", "text": "Self-contained question that names the step."}
  ]
}
```

## Rules checked by `rwo submit`

1. `workflow` and `step` match the step under review exactly.
2. Every automatic finding (A1, A2, ...) is answered: `confirmed` or `discarded`, always with a `reason`.
3. Every confirmed automatic finding appears in `findings` (`"from"` lists its ID; several IDs of the same problem can share one finding, for example `"A3,A4"`).
4. Priorities use the allowed values. `priority` is the highest priority among the findings (or `no-change-needed` if there are none).
5. If there are findings, `proposed_code` contains at least one `// [CHANGE]` and passes `node --check`.
6. Rules confirmed with `"fixed_in_code": true` must no longer be detected in `proposed_code`.
7. At least 2 sandbox tests, with test data only.
8. No personal data: no real national IDs or phone numbers (use `000-0000000-0`, `<test phone>`).
9. Questions are self-contained: they name the step or the workflow.
