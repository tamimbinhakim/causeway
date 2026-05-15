"""Plugin registry + lifecycle tests."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from quay.plugins import (
    all_ready,
    clear,
    register,
    registered,
    shutdown_all,
    startup_all,
)


class _Recorder:
    """Plugin that records lifecycle calls for assertions."""

    contract_version: ClassVar[str] = "v1.0"

    def __init__(self, name: str, *, ready_after: int = 0) -> None:
        self.name = name
        self.calls: list[str] = []
        self._ready_after = ready_after
        self._tick = 0

    async def startup(self, settings: Any) -> None:
        del settings
        self.calls.append("startup")

    async def shutdown(self) -> None:
        self.calls.append("shutdown")

    async def ready(self) -> bool:
        self._tick += 1
        return self._tick >= self._ready_after


@pytest.fixture(autouse=True)
def _isolated_registry() -> Any:
    clear()
    yield
    clear()


async def test_register_dedupes_by_identity() -> None:
    r = _Recorder("a")
    register(r)
    register(r)  # same instance
    assert registered() == [r]


async def test_startup_runs_in_registration_order() -> None:
    a = _Recorder("a")
    b = _Recorder("b")
    register(a)
    register(b)
    await startup_all(settings=None)
    assert a.calls == ["startup"]
    assert b.calls == ["startup"]


async def test_shutdown_is_reverse_of_registration() -> None:
    order: list[str] = []

    class P:
        contract_version: ClassVar[str] = "v1.0"

        def __init__(self, label: str) -> None:
            self.label = label

        async def startup(self, settings: Any) -> None:
            del settings

        async def shutdown(self) -> None:
            order.append(self.label)

        async def ready(self) -> bool:
            return True

    register(P("first"))
    register(P("second"))
    register(P("third"))

    await startup_all(settings=None)
    await shutdown_all()

    assert order == ["third", "second", "first"]


async def test_ready_aggregated() -> None:
    a = _Recorder("a", ready_after=1)
    b = _Recorder("b", ready_after=2)
    register(a)
    register(b)
    snap = await all_ready()
    # First poll: a ready (1>=1), b not yet.
    assert "_Recorder" in next(iter(snap))  # naming sane
    values = list(snap.values())
    assert values[0] is True
    assert values[1] is False


async def test_unknown_contract_version_warns() -> None:
    class WeirdVersion:
        contract_version: ClassVar[str] = "v9.9"

        async def startup(self, settings: Any) -> None:
            del settings

        async def shutdown(self) -> None: ...

        async def ready(self) -> bool:
            return True

    with pytest.warns(UserWarning, match="v9.9"):
        register(WeirdVersion())


async def test_no_contract_version_warns() -> None:
    class NoVersion:
        async def startup(self, settings: Any) -> None:
            del settings

        async def shutdown(self) -> None: ...

        async def ready(self) -> bool:
            return True

    with pytest.warns(UserWarning, match="without contract_version"):
        register(NoVersion())


async def test_shutdown_swallows_per_plugin_errors() -> None:
    class Bad:
        contract_version: ClassVar[str] = "v1.0"

        async def startup(self, settings: Any) -> None:
            del settings

        async def shutdown(self) -> None:
            raise RuntimeError("kaboom")

        async def ready(self) -> bool:
            return True

    register(Bad())
    # Must not raise — shutdowns must isolate errors per plugin.
    await shutdown_all()
