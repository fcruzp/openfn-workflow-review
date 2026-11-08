// R12: per-item loop where one failure stops all the others.
const L = require('../lib');
module.exports = {
  id: 'R12', priority: 'fix-before-production',
  title: 'One failed item stops the whole loop',
  explain: 'Inside each(...), the operation for every item runs without its own error handling. If one item fails, the step stops and the remaining items are not processed, and the log does not say which item failed.',
  fix: 'Wrap the per-item operation in withTryCatch(...): log and skip errors that affect only that item (400, 409, 422), and stop only on errors that affect everyone.',
  check(ctx) {
    const out = [];
    L.walk.full(ctx.ast, n => {
      if (L.calleeName(n) !== 'each' || !n.arguments[1]) return;
      const op = n.arguments[1];
      const name = L.calleeName(op);
      if (name && (L.HTTP_OPS.has(name) || L.NOTIFY_OPS.has(name))) out.push({ line: L.line(n), evidence: L.snippet(ctx.code, n, 80) });
    });
    return out;
  },
};
