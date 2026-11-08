// R03: calls to external systems with no friendly error handling.
const L = require('../lib');
module.exports = {
  id: 'R03', priority: 'fix-before-production',
  title: 'Call to an external system without error handling',
  explain: 'If the system rejects the call or is down, the run fails with the raw adaptor error, which does not say what happened or what to check.',
  fix: 'Add .catch((e, state) => { throw new Error(friendlyError(...)) }), or wrap per-item calls in withTryCatch(...).',
  check(ctx) {
    const ops = new Set([...L.HTTP_OPS, ...L.NOTIFY_OPS]);
    return L.opCalls(ctx.ast, ops)
      .filter(c => !L.hasCatch(c.ancestors, c.node) && !L.wrappedByCall(c.ancestors, c.node))
      .filter(c => !c.ancestors.some(a => a.type === 'TryStatement'))
      .map(c => ({ line: L.line(c.node), evidence: L.snippet(ctx.code, c.node, 80) }));
  },
};
