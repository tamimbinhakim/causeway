"""URL translation rules from docs/routing.md."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from quay._paths import url_for


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("index.py", "/"),
        ("health.py", "/health"),
        ("users/index.py", "/users"),
        ("users/[id].py", "/users/{id}"),
        ("users/[id]/posts.py", "/users/{id}/posts"),
        ("(admin)/stats.py", "/stats"),
        ("(admin)/users.py", "/users"),
        ("billing/webhooks.py", "/billing/webhooks"),
        ("a/(group-x)/b/[id].py", "/a/b/{id}"),
    ],
)
def test_url_for(rel: str, expected: str) -> None:
    assert url_for(PurePosixPath(rel)) == expected


def test_catchall_reserved() -> None:
    with pytest.raises(NotImplementedError, match="catch-all"):
        url_for(PurePosixPath("docs/[...rest].py"))


def test_non_py_rejected() -> None:
    with pytest.raises(ValueError, match=r"\.py"):
        url_for(PurePosixPath("index.ts"))
