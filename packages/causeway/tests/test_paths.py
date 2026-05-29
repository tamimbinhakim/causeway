"""URL translation rules from docs/building/routing/."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from causeway._paths import public_path_for, route_key_for, scope_groups_for, url_for


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("index.py", "/"),
        ("health.py", "/health"),
        ("users/index.py", "/users"),
        ("users/$id.py", "/users/{id}"),
        ("users/$id/posts.py", "/users/{id}/posts"),
        (
            "cases/$slug/ai/pending-actions/bulk.py",
            "/cases/{slug}/ai/pending-actions/bulk",
        ),
        ("(admin)/stats.py", "/stats"),
        ("(admin)/users.py", "/users"),
        ("billing/webhooks.py", "/billing/webhooks"),
        ("a/(group-x)/b/$id.py", "/a/b/{id}"),
    ],
)
def test_url_for_folder_style(rel: str, expected: str) -> None:
    assert url_for(PurePosixPath(rel)) == expected


@pytest.mark.parametrize(
    "rel",
    [
        "users.$id.index.py",
        "users.$id.py",
        "posts.$slug.py",
        "api.v1.health.py",
        "api/v1.$version/posts.py",
        "(admin).stats.py",
        "billing.webhooks.index.py",
    ],
)
def test_dotted_route_files_rejected(rel: str) -> None:
    with pytest.raises(ValueError, match="dotted route files"):
        url_for(PurePosixPath(rel))


def test_root_dynamic_segment() -> None:
    assert url_for(PurePosixPath("$id.py")) == "/{id}"


def test_route_group_leaf_rejected() -> None:
    with pytest.raises(ValueError, match="route groups must be folders"):
        url_for(PurePosixPath("(admin).py"))


def test_folder_catchall_reserved() -> None:
    with pytest.raises(NotImplementedError, match="catch-all"):
        url_for(PurePosixPath("docs/$$rest.py"))


def test_leaf_catchall_reserved() -> None:
    with pytest.raises(NotImplementedError, match="catch-all"):
        url_for(PurePosixPath("$$rest.py"))


@pytest.mark.parametrize("rel", ["users/[id].py", "users/[id]/posts.py"])
def test_bracket_params_rejected(rel: str) -> None:
    with pytest.raises(ValueError, match="bracket route params"):
        url_for(PurePosixPath(rel))


def test_non_py_rejected() -> None:
    with pytest.raises(ValueError, match=r"\.py"):
        url_for(PurePosixPath("index.ts"))


def test_public_route_key_preserves_file_param_syntax() -> None:
    rel = PurePosixPath("(org)/customers/$id/screen.py")
    assert public_path_for(rel) == "/customers/$id/screen"
    assert route_key_for("POST", rel) == "POST /customers/$id/screen"
    assert scope_groups_for(rel) == ("org",)
