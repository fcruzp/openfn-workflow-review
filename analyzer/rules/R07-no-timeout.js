// R07: HTTP calls without an explicit timeout.
const L = require('../lib');
module.exports = {
  id: 'R07', priority: 'optional',
  title: 'HTTP call without an explicit timeout',
  explain: 'Without a timeout option, language-http waits up to 5 minutes (300000 ms) for an answer. A slow system can hold the run for a long time. A timeout does not cancel the operation on the server.',
  fix: 'Add timeout (in ms) to the options, for example { timeout: 30000 }, and handle UND_ERR_HEADERS_TIMEOUT with a friendly message.',
  check(ctx) {
    return L.opCalls(ctx.ast, L.HTTP_OPS).filter(c => {
      const opts = c.node.arguments[L.BODY_OPS.has(c.name) ? 2 : 1];
      if (!opts || opts.type !== 'ObjectExpression') return true;
      return !opts.properties.some(p => p.key && (p.key.name === 'timeout' || p.key.value === 'timeout'));
    }).map(c => ({ line: L.line(c.node), evidence: L.snippet(ctx.code, c.node, 80) })).slice(0, 5);
  },
};
