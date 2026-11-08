// R04: list fetch with paging signs and no loop to fetch the other pages.
const L = require('../lib');
const PAGING = /\b(page|pageSize|page_size|per_page|limit|offset|cursor|nextPage|next_page|skip|top)\b/i;
module.exports = {
  id: 'R04', priority: 'blocking',
  title: 'Possible paged API read without fetching every page',
  explain: 'The call or its response uses paging terms (page, limit, offset, next, cursor, total...), but the code has no loop to fetch the next pages. If the API pages its results, every record after the first page is silently lost.',
  fix: 'Confirm the API paging rules (documentation or client). If it pages, fetch all pages in a loop with a safety cap and log how many pages and records were read.',
  check(ctx) {
    const hasLoop = /\b(while|for)\s*\(/.test(ctx.code);
    if (hasLoop) return [];
    const out = [];
    L.opCalls(ctx.ast, new Set(['get', 'request'])).forEach(c => {
      const text = ctx.code.slice(c.node.start, c.node.end);
      if (PAGING.test(text)) out.push({ line: L.line(c.node), evidence: L.snippet(ctx.code, c.node, 100) });
    });
    L.walk.full(ctx.ast, n => {
      if (n.type === 'MemberExpression' && !n.computed && ['next', 'nextPage', 'next_page', 'total', 'totalPages', 'hasMore', 'has_more'].includes(n.property.name)) {
        const p = L.memberPath(n) || '';
        if (p.includes('data') || p.includes('response')) out.push({ line: L.line(n), evidence: p });
      }
    });
    return out.slice(0, 3);
  },
};
