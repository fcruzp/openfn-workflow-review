// Fixture: no rule should fire. Invented data only.
const friendlyError = (system, action, e) => `${system} failed while trying to ${action}`;
const withTryCatch = op => async state => {
  try { return await op(state); } catch (e) { console.error(`Item failed (code ${e.statusCode})`); return state; }
};
fn(state => {
  if (!state.token) throw new Error('No token from the previous step.');
  return { ...state, items: state.data.items };
});
post('cases', state => ({ id: state.id }), {
  headers: state => ({ Authorization: `Bearer ${state.token}` }),
  timeout: 30000,
}).catch((e, state) => { throw new Error(friendlyError('Target', 'create the case', e)); });
each('$.items[*]', withTryCatch(post('items', state => state.data, { timeout: 30000 })));
fn(state => { console.log(`Processed ${state.items.length} items`); return state; });
