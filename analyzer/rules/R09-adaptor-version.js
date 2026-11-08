// R09: adaptor not pinned to a fixed version.
module.exports = {
  id: 'R09', priority: 'fix-before-production',
  title: 'Adaptor not pinned to a fixed version',
  explain: 'With @latest (or no version), a new adaptor release can change behavior without anyone touching the workflow.',
  fix: 'Pin the adaptor to the exact version that was tested, for example @openfn/language-http@7.3.3.',
  check(ctx) {
    const a = ctx.adaptor || '';
    if (!a) return [];
    return /@latest$/.test(a) || !/@\d+\.\d+\.\d+/.test(a) ? [{ line: null, evidence: a }] : [];
  },
};
