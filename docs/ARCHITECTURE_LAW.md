# ARCHITECTURE LAW

NEVER place Python files on repository root.

Repository root is reserved for:

* pyproject.toml
* README.md
* LICENSE
* .gitignore
* configuration files
* documentation

Forbidden on root:

* *.py
* executable scripts
* utility scripts
* migration scripts
* test runners
* temporary tooling

Required locations:

* src/<package>/        → library code
* scripts/             → executable entrypoints
* tests/               → test code
* tools/               → development tooling
* docs/                → documentation

Before creating any new Python file:

1. Check whether a suitable directory already exists.
2. If not, create an appropriate subdirectory.
3. NEVER place the file on root.

If a Python file is found on root:

1. Consider it architecture debt.
2. Propose relocation.
3. Update references.
4. Verify execution.
5. Remove the root copy.

ROOT SHALL CONTAIN ZERO PYTHON FILES.

This rule overrides convenience, habit, and temporary workarounds.
