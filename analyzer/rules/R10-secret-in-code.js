// R10: secrets or tokens written in the code.
const L = require('../lib');
const KEY = /(password|passwd|secret|token|api[_-]?key|apikey|authorization|access[_-]?key)/i;
module.exports = {
  id: 'R10', priority: 'blocking',
  title: 'Secret written in the code',
  explain: 'A password, token or key written in the code is visible to everyone who can see the workflow and stays in its history. Secrets belong in Lightning credentials.',
  fix: 'Move the value to the step credential and read it from state.configuration. Then rotate the exposed secret.',
  check(ctx) {
    const out = [];
    const isSecretLiteral = (v) => typeof v === 'string' && v.length >= 12 && !/\s/.test(v) && !/^(https?:|\/)/.test(v);
    L.walk.full(ctx.ast, n => {
      if (n.type === 'Property' && n.value.type === 'Literal') {
        const k = n.key.name || n.key.value || '';
        if (KEY.test(k) && isSecretLiteral(n.value.value)) out.push({ line: L.line(n), evidence: `${k}: "…"` });
      }
      if (n.type === 'VariableDeclarator' && n.init && n.init.type === 'Literal' && n.id.type === 'Identifier' &&
          KEY.test(n.id.name) && isSecretLiteral(n.init.value)) out.push({ line: L.line(n), evidence: `${n.id.name} = "…"` });
      if (n.type === 'Literal' && typeof n.value === 'string' && /^(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{12,}$/.test(n.value)) {
        out.push({ line: L.line(n), evidence: `"${n.value.split(' ')[0]} …"` });
      }
    });
    return out;
  },
};
