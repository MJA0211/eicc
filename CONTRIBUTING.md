# Working on EICC

Fork the repository and open a pull request to propose a change. Only the owner
has write access. Changes from contributors need the owner's review before they
can be merged. Contributions are covered by the [MIT License](LICENSE).

Read [the architecture](docs/architecture.md), [capability traceability](docs/requirements-traceability.md), and
[security and operations](docs/security-and-operations.md) before changing lifecycle rules. Keep the fictional
scenario disclosure intact. Do not add real credentials, production data, fabricated test evidence, or invented
business outcomes.

Use Python 3.11+, uv, Node 22, and the checked-in lockfiles. Follow the README for local setup. Update typed
schemas and migrations when persistence changes. Use `uv run alembic revision --autogenerate -m "description"`
to draft a migration, then review and test both upgrade and downgrade. Do not replace migration history or rely
on `create_all` at application startup.

Test the changed behavior, including its authorization and failure paths. Changes to scope, mappings, tests,
or acceptance must preserve evidence invalidation and live release checks. Avoid tests that merely repeat
implementation expressions; assert user-visible or persisted outcomes.

```sh
uv run ruff check .
uv run ruff format --check backend tests migrations scripts
uv run pytest --cov=backend --cov-report=term-missing
npm --prefix frontend run build
npm --prefix frontend test
```

Run PostgreSQL and deployed browser verification for persistence, middleware, proxy, or container changes.
CI also audits dependencies. Install root formatting tooling with `npm ci`; `npm run format` formats repository
Markdown, frontend sources, and supported configuration. Python formatting is handled by Ruff.

Browser tests create fictional records and export screenshots. Use the isolated default test server unless
deliberately verifying a disposable demo deployment via `EICC_BASE_URL`. Do not point this suite at a private
non-demo environment. Keep test results, local databases, logs, and `.env` out of Git.

Document concrete behavior, validation commands, and any limits in the change description. Do not claim a
remote CI run, external integration, stakeholder decision, or deployment occurred without evidence.
