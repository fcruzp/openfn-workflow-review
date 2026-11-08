"""Verified adaptor facts, attached to each step so the model does not need to re-test them."""

FACTS = {
    "common": [
        "each(...): after the loop, state.data holds only the last operation's response.",
        ".catch((e, state) => ...) works on operations.",
        "Lightning: cron runs in UTC; a cron run starts from the final state of the last successful run "
        "(manual runs included); a run is Failed if a final step fails; credential values are scrubbed from logs.",
    ],
    "language-http": [
        "post/put/patch(path, body, options): options passed as a function are silently ignored; "
        "use { headers: state => ({...}) }. get(path, options) does expand a function.",
        "Status 400 or above throws an error with statusCode, body and url; the response body becomes state.data.",
        "await get(path, options)(state) inside fn returns the next state with the body in .data.",
        "Auth: Bearer from access_token, or Basic from username/password, only if Authorization is not already set.",
        "The adaptor logs the full URL including the query string.",
        "Default timeout 300000 ms; option `timeout` in ms; a timeout throws UND_ERR_HEADERS_TIMEOUT "
        "(no status code) and does not cancel the operation on the server.",
    ],
    "language-twilio": [
        "Twilio errors carry .status and .code (not statusCode); phone numbers must be E.164.",
    ],
}
VERIFIED_FOR = "language-common 3.3.5, language-http 7.3.3, OpenFn CLI 1.45.2"


def for_adaptor(adaptor):
    out = list(FACTS["common"])
    for key, facts in FACTS.items():
        if key != "common" and key in (adaptor or ""):
            out += facts
    return out
