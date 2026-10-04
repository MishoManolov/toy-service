# Project context

Purpose: in-memory URL shortener with a WSGI JSON API. Behaviour spec: README.md.

Layout
- src/toy_service/shortener.py: domain logic (Shortener, Link, errors)
- src/toy_service/app.py: WSGI app (create_app)
- tests/: pytest; tests/helpers.py has `call` for exercising the WSGI app

Conventions
- Pure stdlib, Python 3.12, type hints everywhere, ruff for lint and format.
- Domain errors live in shortener.py; the app maps them to HTTP status codes.

Definition of done: ruff clean, tests green, README updated if behaviour changed.
