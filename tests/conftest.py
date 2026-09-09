"""Fail the whole suite if any test is skipped.

The vendored fixture corpus must always run. A skip means a fixture or the
corpus itself is missing -- the silent-failure class the predecessor shipped
(39 of 40 tests skipped, suite still green). Guarding here, in the suite,
means every `pytest` invocation enforces it with no shell wrapper, no summary
file, and no interpreter-specific one-liner to duplicate per workflow.
"""

from __future__ import annotations

import pytest


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    stats = getattr(reporter, "stats", None)
    if isinstance(stats, dict) and stats.get("skipped"):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
