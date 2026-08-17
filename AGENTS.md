# Repository development instructions

## Development rules

- Remove unused code, comments, wrappers, and unnecessary error handling.
- Do not hide failures. Fix the underlying cause instead of converting errors into success.
- Keep Python modules under `src/boothitemmanager2/` and executable maintenance code under `scripts/`; do not add Python modules at the repository root.
- Follow [docs/ARCHITECTURE_LAW.md](docs/ARCHITECTURE_LAW.md) for the current source layout constraints.
- Preserve the distinction between seller-stated facts, observed values, derived data, and unknown values described in [README.md](README.md).

## Commands

- Build: `task build`
- Test: `task test`
- Lint, format, and test: `task check`
- Local preview: `task serve` (`http://localhost:8080`)

Before submitting a change, run the smallest relevant checks and then `task check` when the project dependencies needed by that command are available.
