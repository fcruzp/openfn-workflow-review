// Fixture: every rule should fire at least once. Invented data only.
const token = state.data.token;                              // R06
get('records?page=1&pageSize=100', { headers: {} });         // R03 R04 R07
post('cases', state => ({ id: 1 }), state => ({              // R01 R03 R07
  headers: { Authorization: `Bearer ${state.token}` },       // R11
}));
get(`people/${state.data.telefono}`);                        // R03 R05 R07
fn(state => {
  console.log('phones', state.data);                         // R05
  const since = '2026-06-16';                                // R08
  const apiKey = 'sk_live_abcdefghijklmnop';                 // R10
  return state;
});
each('$.items[*]', post('items', state => state.data));      // R12 R03 R07
fn(state => ({ ...state, all: state.data }));                // R02
