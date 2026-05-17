"""URL translation rules from docs/building/routing/."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from causeway._paths import url_for


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
def test_url_for_folder_style(rel: str, expected: str) -> None:
    assert url_for(PurePosixPath(rel)) == expected


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("users.$id.index.py", "/users/{id}"),
        ("users.$id.py", "/users/{id}"),
        ("posts.$slug.py", "/posts/{slug}"),
        ("api.v1.health.py", "/api/v1/health"),
        ("api.v1.users.$id.posts.$postId.py", "/api/v1/users/{id}/posts/{postId}"),
        ("(admin).stats.py", "/stats"),
        ("(admin).users.py", "/users"),
        ("billing.webhooks.index.py", "/billing/webhooks"),
    ],
)
def test_url_for_dot_flat_style(rel: str, expected: str) -> None:
    assert url_for(PurePosixPath(rel)) == expected


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("api/v1.$version.posts.py", "/api/v1/{version}/posts"),
        ("(admin)/users.$id.py", "/users/{id}"),
        ("users/[id]/posts.$postId.py", "/users/{id}/posts/{postId}"),
        ("$id.py", "/{id}"),
        ("$id.index.py", "/{id}"),
    ],
)
def test_url_for_mixed_style(rel: str, expected: str) -> None:
    assert url_for(PurePosixPath(rel)) == expected


def test_folder_catchall_reserved() -> None:
    with pytest.raises(NotImplementedError, match="catch-all"):
        url_for(PurePosixPath("docs/[...rest].py"))


def test_leaf_catchall_reserved() -> None:
    with pytest.raises(NotImplementedError, match="catch-all"):
        url_for(PurePosixPath("docs.$$rest.py"))


def test_non_py_rejected() -> None:
    with pytest.raises(ValueError, match=r"\.py"):
        url_for(PurePosixPath("index.ts"))
