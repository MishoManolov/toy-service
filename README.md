# toy-service

Tiny in-memory URL shortener. Sample target for the software factory.

## Run
`uv run python -m toy_service` serves on http://127.0.0.1:8000.

## Behaviour
- `POST /shorten` with JSON `{"url": "...", "ttl": seconds (optional)}` returns 201 `{"code", "short_url"}`.
- Only absolute `http` and `https` URLs with a host are accepted. Anything else is a 400.
- Leading and trailing whitespace around the URL is ignored.
- Malformed or incomplete request bodies are a 400, never a 500.
- Every link gets a unique code. Creating a link never replaces an existing one.
- `GET /<code>` returns 302 with a `Location` header.
- A link with a ttl is expired from the moment `created_at + ttl` is reached. Expired links behave like unknown links (404).
- A hit is counted only when a link resolves successfully.
