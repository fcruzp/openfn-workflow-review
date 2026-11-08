// R01: post/put/patch with the options passed as a function: the adaptor silently ignores them.
const L = require('../lib');
module.exports = {
  id: 'R01', priority: 'blocking',
  title: 'Request options passed as a function are ignored',
  explain: 'In language-http 7.x, post/put/patch only expand a function inside the options object, not the whole options argument. Passed as a function, the options (and the headers in them) never go out, which typically ends in a 401.',
  fix: 'Pass an object whose values can be functions: { headers: state => ({ ... }) }.',
  check(ctx) {
    return L.opCalls(ctx.ast, L.BODY_OPS)
      .filter(c => L.isFn(c.node.arguments[2]))
      .map(c => ({ line: L.line(c.node), evidence: L.snippet(ctx.code, c.node) }));
  },
};
