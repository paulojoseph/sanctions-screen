# Contributing

Small project, small rules. Open an issue before a big change.

- `pip install -e ".[dev]"`, then `pytest` and `ruff check .` (the full suite takes about a minute).
- Tests never touch the network. Only `fetch` does, and it is not covered by tests.
- Entity ids (`source:uid`) are stable on purpose: reviewer decisions in
  `data/decisions/decisions.jsonl` are keyed on them. Do not change how an id is built.
- Fixtures in `tests/fixtures/` stay in the exact format the publishers use. Never
  reformat or pretty-print them; regenerate with `python scripts/make_fixtures.py`.
- A new runtime dependency needs a line in the "Why these libraries" table in the README.
- Keep changes small and add a test next to the code you touch.
- Run `ruff check .` before you push. A few old warnings are known, don't add new ones.
- Be kind in reviews. This is a screening aid, not a decision maker.
