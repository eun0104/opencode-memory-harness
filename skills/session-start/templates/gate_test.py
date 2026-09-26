"""Gates for plan leaf <leaf>: <plan item heading>.

Plan: <plan-path> -> <plan item>

One test per acceptance criterion, written before the code. When a gate passes, remove its
xfail marker in the same commit. Changing an assertion or a tolerance needs an ADR.
Mark slow tests (simulations, fits) with @pytest.mark.slow.
"""

import pytest


@pytest.mark.xfail(strict=True, raises=(AssertionError, NotImplementedError),
                   reason="gate: <measurable criterion, e.g. mobility within 5% of data at 300 K>")
def test_<criterion>():
    measured, limit = <compute>, <limit>
    assert measured <= limit, f"<quantity>: {measured} > {limit}"


@pytest.mark.xfail(strict=True, reason="blocked: <what is missing, e.g. 77 K data from fab>")
def test_<blocked_criterion>():
    raise NotImplementedError
