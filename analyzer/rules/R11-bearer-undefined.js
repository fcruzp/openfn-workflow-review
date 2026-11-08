// R11: Bearer header built from a value that may be undefined.
const L = require('../lib');
module.exports = {
  id: 'R11', priority: 'blocking',
  title: 'Authorization header built from a value that may be missing',
  explain: 'The header is built as `Bearer ${value}` without checking the value exists. If the previous step did not return it, the request goes out as "Bearer undefined" and the system answers 401, which hides the real cause.',
  fix: 'Check the value before the request and throw a friendly error that says which step should have returned it.',
  check(ctx) {
    const guarded = L.guardedNames(ctx.ast);
    const out = [];
    L.walk.full(ctx.ast, n => {
      if (n.type !== 'TemplateLiteral' || !n.quasis.length || !/Bearer\s*$/.test(n.quasis[0].value.cooked || '')) return;
      const e = n.expressions[0];
      if (!e) return;
      const name = e.type === 'Identifier' ? e.name : L.memberPath(e);
      const short = name && name.split('.').pop();
      if (name && !guarded.has(name) && !guarded.has(short)) out.push({ line: L.line(n), evidence: L.snippet(ctx.code, n) });
    });
    return out;
  },
};
