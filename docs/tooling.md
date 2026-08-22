# Development quality gates

This repository is a Python project with browser-delivered static JavaScript. There is no `package.json`, TypeScript workspace, or multi-project monorepo, so Biome, Oxlint, `tsc`, Zod, and Nx are intentionally not installed.

## Ownership

| Concern | Owner | Command |
| --- | --- | --- |
| dependency resolution | uv | `uv lock --check` / `uv sync --locked` |
| Python lint | Ruff | `uv run --locked ruff check src scripts tests` |
| Python format | Ruff | `uv run --locked ruff format --check src scripts tests` |
| Python types | Pyrefly | `uv run --locked pyrefly check --summarize-errors` |
| fast tests | pytest | `uv run --locked pytest tests --ignore=tests/e2e -q` |
| static JavaScript syntax | Node.js | `node --check ...` in CI |
| browser integration | Playwright | PR CI only |

`ruff format --check` is deliberately non-mutating. The mutating formatter is exposed separately as `task format`.

## Fresh clone

```bash
uv sync --locked
uv run --locked python scripts/check.py
```

To install the same fast gate as a Git hook:

```bash
uv run --locked prek install
```

`prek.toml` executes the same `scripts/check.py` gate as CI; there is no second set of local-only rules.

## Validation boundary

Pydantic strict validation is used at the BOOTH network observation boundary. Internal normalized objects are not repeatedly revalidated. This keeps external parsing fail-fast without adding validation layers inside trusted transformations.

## Type-check scope

Pyrefly owns type checking. The initial enforced scope is the actively maintained refresh/cache/build path declared in `[tool.pyrefly]`. Legacy analytical modules remain outside the enforced type scope until migrated; no competing type checker is installed.

## CI timing

The PR workflow records the fast gate elapsed time in `scripts/check.py`; GitHub Actions provides the full build-and-browser duration. The baseline immediately before this migration is recorded from the existing PR workflow, and the post-migration value is recorded after the quality-gate PR runs on the same `ubuntu-latest` class. These measurements are operational observations, not performance guarantees.
