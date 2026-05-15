"""env() helper, plugin.requires enforcement, settings_fragment merging."""

from __future__ import annotations

import os
from typing import Any, ClassVar

import pytest

from causeway.plugins import (
    check_required_contracts,
    clear,
    env,
    merge_settings_fragments,
    register,
)


@pytest.fixture(autouse=True)
def _reset() -> Any:
    clear()
    yield
    clear()


def test_env_defaults_to_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CAUSEWAY_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    assert env() == "dev"


def test_env_reads_causeway_env_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("CAUSEWAY_ENV", "staging")
    assert env() == "staging"


def test_env_falls_back_to_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CAUSEWAY_ENV", raising=False)
    monkeypatch.setenv("ENV", "prod")
    assert env() == "prod"


class _Base:
    contract_version: ClassVar[str] = "v1.0"

    async def startup(self, settings: Any) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool:
        return True


def test_required_contract_satisfied() -> None:
    class TaskAdapterImpl(_Base):
        pass

    class Worker(_Base):
        requires: ClassVar[list[str]] = ["TaskAdapterImpl"]

    register(TaskAdapterImpl())
    register(Worker())
    check_required_contracts()  # no raise


def test_required_contract_missing_raises() -> None:
    class Worker(_Base):
        requires: ClassVar[list[str]] = ["KV", "DBSession"]

    register(Worker())
    with pytest.raises(RuntimeError, match="requires"):
        check_required_contracts()


def test_settings_fragment_merges_into_settings() -> None:
    class WithFragment(_Base):
        def settings_fragment(self) -> dict[str, Any]:
            return {"redis_url": "redis://localhost", "feature_flags": {"new_ui": True}}

    register(WithFragment())

    class _S:
        env = "dev"

    out = merge_settings_fragments(_S())
    assert out.redis_url == "redis://localhost"
    assert out.feature_flags == {"new_ui": True}


def test_settings_fragment_doesnt_overwrite_existing_fields() -> None:
    class WithFragment(_Base):
        def settings_fragment(self) -> dict[str, Any]:
            return {"redis_url": "redis://override"}

    register(WithFragment())

    class _S:
        redis_url = "redis://app-controlled"

    out = merge_settings_fragments(_S())
    assert out.redis_url == "redis://app-controlled"


# Cleanup any env leakage between tests.
@pytest.fixture(autouse=True)
def _env_isolation(monkeypatch: pytest.MonkeyPatch) -> Any:
    for k in ("CAUSEWAY_ENV", "ENV"):
        if k in os.environ:
            monkeypatch.delenv(k, raising=False)
    return
