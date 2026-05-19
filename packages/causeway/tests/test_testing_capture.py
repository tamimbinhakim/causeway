"""Smoke test for captured() and captured_webhooks()."""

import pytest

from causeway.events import Event, _reset_registry
from causeway.tasks import _clear
from causeway.testing import captured, captured_webhooks
from causeway.webhooks import Subscriber, set_store


@pytest.fixture(autouse=True)
def _reset():
    _reset_registry()
    _clear()
    set_store(None)
    yield
    _reset_registry()
    _clear()
    set_store(None)


async def test_captured_listeners_short_circuited():
    class CustomerCreated(Event):
        id: str

    real_calls = []

    @CustomerCreated.listen
    async def real(p):
        real_calls.append(p.id)

    async with captured(CustomerCreated) as caps:
        await CustomerCreated(id="u1").emit()
    assert len(caps) == 1
    assert caps[0].id == "u1"
    assert real_calls == []  # listener short-circuited

    # After block, original listener restored.
    await CustomerCreated(id="u2").emit()
    assert real_calls == ["u2"]


async def test_captured_webhooks_records_subscriber():
    class Ev(Event):
        webhook = True
        id: str

    Subscriber(url="https://x.example", secret="s", events=[Ev])
    async with captured_webhooks() as deliveries:
        await Ev(id="u").emit()
    assert len(deliveries) == 1
    assert deliveries[0].url == "https://x.example"
    assert deliveries[0].event_name == "ev"
