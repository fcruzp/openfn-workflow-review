// R02: state.data used after each(...) as if it still held the whole list.
const L = require('../lib');
module.exports = {
  id: 'R02', priority: 'blocking',
  title: 'state.data used after each() as if it held the whole list',
  explain: 'After each(...), state.data holds only the response of the last operation run inside the loop. Code after the loop that reads state.data gets one item (or none), not the full list.',
  fix: 'Save the list in its own state key before the each(), and read that key afterwards.',
  check(ctx) {
    const body = ctx.ast.body;
    const idx = body.findIndex(s => s.type === 'ExpressionStatement' && L.calleeName(s.expression) === 'each');
    if (idx < 0) return [];
    const out = [];
    body.slice(idx + 1).forEach(stmt => L.walk.full(stmt, n => {
      if (n.type === 'MemberExpression' && L.memberPath(n) === 'state.data') {
        out.push({ line: L.line(n), evidence: L.snippet(ctx.code, stmt, 100) });
      }
    }));
    return out.slice(0, 3);
  },
};
