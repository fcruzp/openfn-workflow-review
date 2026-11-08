# Reusable code patterns

Each step needs its own copy of a helper, because steps do not share code in OpenFn.

```js
// Translates a technical error into a friendly log message
const friendlyError = (system, action, e) => {
  const c = e.statusCode ?? e.status; // http adaptor: statusCode; Twilio: status
  if (c === 401 || c === 403) return `${system} rejected the credential while trying to ${action}. Check the step's credential.`;
  if (c === 404) return `${system} could not find the address while trying to ${action}. Check the credential's baseUrl.`;
  if (c >= 500) return `${system} had an internal error while trying to ${action} (code ${c}). Try again later or contact the ${system} team.`;
  if (c >= 400) return `${system} did not accept the request while trying to ${action} (code ${c}).`;
  if (e.code === 'UND_ERR_HEADERS_TIMEOUT' || e.code === 'UND_ERR_BODY_TIMEOUT')
    return `${system} did not respond in time while trying to ${action}. Check in ${system} whether the operation went through before retrying.`;
  if (e.code || e.cause?.code) return `Could not connect to ${system} while trying to ${action} (${e.code || e.cause.code}). Check the network or whether ${system} is available.`;
  return `Unexpected error while trying to ${action}: ${e.message}`;
};

// Single operation: friendly message, then stop
post('path', body, options).catch((e, state) => {
  throw new Error(friendlyError('SourceSystem', 'fetch the requests', e));
});

// Per-item operation inside each(): decide per error whether to continue or stop
const withTryCatch = op => async state => {
  const item = state.data;
  try {
    return await op(state);
  } catch (e) {
    if ([400, 409, 422].includes(e.statusCode)) { // affects only this item
      console.error(`Could not process ${item.id} (code ${e.statusCode}).`);
      return state; // continue with the next item
    }
    throw new Error(friendlyError('TargetSystem', `process ${item.id}`, e)); // affects everyone: stop
  }
};

// Pagination: fetch every page (adapt the field names to the API's documented paging rules)
fn(async state => {
  const all = [];
  const MAX_PAGES = 100; // safety cap
  let page = 1;
  while (page <= MAX_PAGES) {
    const { data } = await get('records', { query: { page, pageSize: 100 } })(state);
    const items = data.results ?? [];
    all.push(...items);
    if (!data.next || items.length === 0) break;
    page++;
  }
  console.log(`Fetched ${all.length} records in ${page} page(s)`);
  return { ...state, records: all };
});
```

Post headers: if the options of `post`/`put`/`patch` are a function they are silently ignored. Use `{ headers: state => ({ ... }) }`.
