// R06: a value received from another system is used without checking it exists.
const L = require('../lib');
module.exports = {
  id: 'R06', priority: 'fix-before-production',
  title: 'Value from another system used without checking it exists',
  explain: 'The step reads a value from a previous response (token, ID, list) and uses it without checking it is there. If the other system answers without it, the step fails later with a confusing error, or sends wrong data.',
  fix: 'Check the value right after reading it and throw a friendly error if it is missing (for lists, check Array.isArray).',
  check(ctx) {
    const guarded = L.guardedNames(ctx.ast);
    const out = [];
    L.walk.full(ctx.ast, n => {
      if (n.type !== 'VariableDeclarator' || !n.init || n.id.type !== 'Identifier') return;
      const p = n.init.type === 'MemberExpression' ? L.memberPath(n.init) : null;
      if (p && /^state\.data\.\w+/.test(p) && !guarded.has(n.id.name)) {
        out.push({ line: L.line(n), evidence: L.snippet(ctx.code, n, 100) });
      }
    });
    return out.slice(0, 5);
  },
};
