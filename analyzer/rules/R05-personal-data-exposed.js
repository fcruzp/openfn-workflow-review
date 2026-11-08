// R05: personal data in URLs, query strings or console.log.
const L = require('../lib');
module.exports = {
  id: 'R05', priority: 'fix-before-production',
  title: 'Personal data may end up in URLs or logs',
  explain: 'The http adaptor logs the full URL, including the query string, and console.log output stays in the run logs. Phone numbers, national IDs, names or message texts there are exposed to anyone who can read the logs.',
  fix: 'Send personal data in the request body, not the URL. Log only counts and IDs that are not personal, or mask values (last 4 digits).',
  check(ctx) {
    const out = [];
    L.opCalls(ctx.ast, L.HTTP_OPS).forEach(c => {
      const url = c.node.arguments[0];
      if (!url) return;
      let hit = null;
      L.walk.full(url, n => {
        if (n.type === 'TemplateLiteral') n.expressions.forEach(e => {
          const t = ctx.code.slice(e.start, e.end); if (L.PERSONAL.test(t)) hit = t;
        });
      });
      const opts = c.node.arguments[L.BODY_OPS.has(c.name) ? 2 : 1];
      if (opts && opts.type === 'ObjectExpression') opts.properties.forEach(p => {
        if (p.key && p.key.name === 'query' && L.PERSONAL.test(ctx.code.slice(p.start, p.end))) hit = 'query';
      });
      if (hit) out.push({ line: L.line(c.node), evidence: L.snippet(ctx.code, c.node, 100) });
    });
    L.walk.full(ctx.ast, n => {
      if (n.type === 'CallExpression' && L.memberPath(n.callee) === 'console.log') {
        const t = ctx.code.slice(n.start, n.end);
        if (L.PERSONAL.test(t) || /state\.data\b(?!\.length)|JSON\.stringify\(\s*state/.test(t)) out.push({ line: L.line(n), evidence: L.snippet(ctx.code, n, 100) });
      }
    });
    return out.slice(0, 5);
  },
};
