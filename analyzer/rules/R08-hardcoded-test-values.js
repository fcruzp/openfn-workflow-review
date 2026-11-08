// R08: hardcoded test values (fixed dates, phone numbers, IDs).
const L = require('../lib');
const DATE = /(?<!\d)(19|20)\d{2}-\d{2}-\d{2}(?!\d)/;
const PHONE = /^\+?\d[\d\s-]{7,14}\d$/;
const NATIONAL_ID = /^\d{3}-?\d{7}-?\d$/;
module.exports = {
  id: 'R08', priority: 'fix-before-production',
  title: 'Hardcoded test value',
  explain: 'A fixed date, phone number or ID in the code usually comes from testing. In production it sends data to the wrong place or always queries the same period.',
  fix: 'Take the value from the data, the state or the credential. If it is only for testing, remove it before production.',
  check(ctx) {
    const out = [];
    L.walk.full(ctx.ast, n => {
      const v = n.type === 'Literal' && typeof n.value === 'string' ? n.value.trim()
        : n.type === 'TemplateElement' ? (n.value.cooked || '').trim() : null;
      if (!v) return;
      const kind = DATE.test(v) ? 'date' : NATIONAL_ID.test(v) ? 'ID' : PHONE.test(v) ? 'phone number' : null;
      if (kind === 'date') out.push({ line: L.line(n), evidence: `date: "${v.match(DATE)[0]}"` });
      else if (kind) out.push({ line: L.line(n), evidence: `${kind}: "${v.slice(0, 4)}\u2026"` });
    });
    return out.slice(0, 5);
  },
};
