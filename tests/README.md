# NUMA test suite

Three groups, split by what they actually exercise and what they need to run.

| Directory              | Imports the app | Needs                      | Run with                         |
| ---------------------- | --------------- | -------------------------- | -------------------------------- |
| `tests/unit/`          | yes             | `server/requirements.txt`  | `pytest tests/unit`              |
| `tests/legacy/`        | no              | `pytest` only              | `pytest tests/legacy`            |
| `tests/secret_checks/` | no              | `pytest`, real env vars    | `pytest tests/secret_checks`     |

Run everything from the repository root: `pytest tests`.

## `tests/unit/` - the real suite

Mirrors `server/src/`, one directory per feature module, so a test for
`src/core/db.py` lives at `tests/unit/core/test_db.py`. `conftest.py` puts
`server/` on the path and sets the two environment variables the modules read at
import.

These tests exercise the application. They are deliberately restricted to logic
that runs without a database, a network call or a model load, so the whole
directory finishes in about a second and can gate every push.

Each test names the defect it guards against in its docstring. That matters more
than it sounds: a regression test whose failure message is a bare assertion
tells the next reader nothing about why the behaviour was chosen.

CI runs this directory by path, not as a list of files, so a new test file is
picked up without anyone remembering to register it.

## `tests/legacy/` - kept, but be clear about what they are

Fifteen files that predate the unit suite. **None of them imports `src/` or
`main.py`**: each defines its own local copy of a function and then asserts on
that copy. A green run of `tests/legacy/` says nothing about whether the
application works.

They were the entire suite until NUMA-143, which is worth knowing when reading
older commits that describe the build as green. They are kept because they are
harmless, fast, and their names map to the CI suites that have always reported
them. New tests belong in `tests/unit/`.

## `tests/secret_checks/` - environment wiring

Checks that the deployment environment carries the variables the app needs, and
that they are shaped correctly (a URL parses, a token has the expected prefix).
Skipped unless `RUN_SECRET_INTEGRATION_TESTS=1`, because they assert on real
configuration rather than on code.

The directory is not named `secrets/`: pytest puts `tests/` on `sys.path`, so a
package by that name shadows the standard library's `secrets` module and breaks
any import of it, including Starlette's.

## Adding a test

Put it under `tests/unit/<module>/test_<thing>.py`, import the real code, and
say in the docstring what breaks if the test fails. If it needs a database or a
network call it does not belong here yet; that is the integration layer, which
does not exist.

Before trusting a new regression test, check it fails against the behaviour it
describes. A test that passes on both the broken and the fixed code is worse
than no test, because it reads like coverage.
