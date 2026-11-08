// Shared helpers for the rules: parsing and small AST utilities.
'use strict';
const acorn = require('./vendor/acorn.js');
const walk = require('./vendor/walk.js');

const HTTP_OPS = new Set(['get', 'post', 'put', 'patch', 'del', 'request', 'head', 'options']);
const BODY_OPS = new Set(['post', 'put', 'patch']);          // (path, body, options)
const NOTIFY_OPS = new Set(['sendSMS', 'sendWhatsApp', 'send']);
const PERSONAL = /(phone|telefono|tel[eé]fono|celular|cedula|c[eé]dula|nombre|name|apellido|email|correo|numero|n[uú]mero|address|direccion)/i;

function parse(code) {
  return acorn.parse(code, {
    ecmaVersion: 'latest', sourceType: 'script', locations: true,
    allowReturnOutsideFunction: true, allowAwaitOutsideFunction: true, allowHashBang: true,
  });
}

const calleeName = (n) => n && n.type === 'CallExpression' && n.callee.type === 'Identifier' ? n.callee.name : null;
const isFn = (n) => n && (n.type === 'ArrowFunctionExpression' || n.type === 'FunctionExpression');
const line = (n) => (n && n.loc ? n.loc.start.line : null);

// "state.data", "state.token", ... -> dotted path string, or null
function memberPath(n) {
  const parts = [];
  while (n && n.type === 'MemberExpression') {
    if (n.computed) return null;
    parts.unshift(n.property.name);
    n = n.object;
  }
  if (n && n.type === 'Identifier') { parts.unshift(n.name); return parts.join('.'); }
  return null;
}

function snippet(code, node, max = 120) {
  const s = code.slice(node.start, node.end).replace(/(^|\s)\/\/[^\n]*/g, ' ').replace(/\s+/g, ' ').trim();
  return s.length > max ? s.slice(0, max - 1) + '…' : s;
}

// Every call to an adaptor operation anywhere in the code (with its parent chain).
function opCalls(ast, names) {
  const out = [];
  walk.ancestor(ast, {
    CallExpression(node, ancestors) {
      const name = calleeName(node);
      if (name && names.has(name)) out.push({ node, name, ancestors: ancestors.slice(0, -1) });
    },
  });
  return out;
}

// Is this call followed by .catch(...) ?
function hasCatch(ancestors, node) {
  const parent = ancestors[ancestors.length - 1];
  return parent && parent.type === 'MemberExpression' && parent.object === node &&
    !parent.computed && parent.property.name === 'catch';
}

// Is the call wrapped by a user function (e.g. withTryCatch(post(...)))?
function wrappedByCall(ancestors, node) {
  const parent = ancestors[ancestors.length - 1];
  return parent && parent.type === 'CallExpression' && parent.arguments.includes(node) &&
    !HTTP_OPS.has(calleeName(parent)) && calleeName(parent) !== 'each';
}

// Identifiers / paths tested in any if/conditional/logical guard
function guardedNames(ast) {
  const names = new Set();
  const collect = (test) => walk.full(test, (n) => {
    if (n.type === 'Identifier') names.add(n.name);
    const p = n.type === 'MemberExpression' ? memberPath(n) : null;
    if (p) names.add(p);
  });
  walk.full(ast, (n) => {
    if (n.type === 'IfStatement' || n.type === 'ConditionalExpression') collect(n.test);
    if (n.type === 'LogicalExpression' && (n.operator === '||' || n.operator === '??')) collect(n.left);
  });
  return names;
}

module.exports = { acorn, walk, parse, calleeName, isFn, line, memberPath, snippet, opCalls,
  hasCatch, wrappedByCall, guardedNames, HTTP_OPS, BODY_OPS, NOTIFY_OPS, PERSONAL };
