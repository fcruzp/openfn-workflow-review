#!/usr/bin/env node
// Usage: node analyze.js <step.js> [--adaptor <adaptor@version>]
// Prints a JSON list of automatic findings. Each one must be confirmed or discarded by the reviewer.
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

const args = process.argv.slice(2);
const file = args[0];
const ai = args.indexOf('--adaptor');
const adaptor = ai >= 0 ? args[ai + 1] : '';
const code = fs.readFileSync(file, 'utf8');

const result = { file: path.basename(file), adaptor, parse_error: null, findings: [] };
let ast = null;
try { ast = L.parse(code); } catch (e) { result.parse_error = `${e.message}`; }

const rulesDir = path.join(__dirname, 'rules');
for (const f of fs.readdirSync(rulesDir).filter(f => /^R\d+.*\.js$/.test(f)).sort()) {
  const rule = require(path.join(rulesDir, f));
  if (!ast && rule.id !== 'R09') continue;
  let hits = [];
  try { hits = rule.check({ ast, code, adaptor }); } catch (e) { hits = []; }
  for (const h of hits) {
    result.findings.push({ rule: rule.id, priority: rule.priority, title: rule.title,
      line: h.line, evidence: h.evidence, explain: rule.explain, fix: rule.fix });
  }
}
process.stdout.write(JSON.stringify(result, null, 2) + '\n');
