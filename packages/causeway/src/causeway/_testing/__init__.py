"""Internal package for the inline-scenario runtime.

Public re-exports live in :mod:`causeway.testing`; this package is
implementation detail and may change between releases.
"""

from __future__ import annotations

from causeway._testing.errors import ScenarioAssertionError
from causeway._testing.expect import Expectation, expect
from causeway._testing.registry import (
    Registry,
    current_registry,
    set_registry,
)
from causeway._testing.response import Response
from causeway._testing.scenario import _It, scenario
from causeway._testing.snapshot import Ellipsis as SnapshotEllipsis
from causeway._testing.snapshot import (
    SnapshotEdit,
    SnapshotValue,
    pending_edits,
    snapshot,
)

__all__ = [
    "Expectation",
    "Registry",
    "Response",
    "ScenarioAssertionError",
    "SnapshotEdit",
    "SnapshotEllipsis",
    "SnapshotValue",
    "_It",
    "current_registry",
    "expect",
    "pending_edits",
    "scenario",
    "set_registry",
    "snapshot",
]
