import asyncio
import sys
from datetime import datetime, timedelta

import pytest

from llmgine.bus.bus import MessageBus, bus_exception_hook
from llmgine.messages import Event, ScheduledEvent


# Handler that prints when called, accepts base Event type
def scheduled_event_handler(event: Event):
    if isinstance(event, ScheduledEvent):
        print(
            f"Handled scheduled event at {datetime.now().isoformat()} with scheduled_time={event.scheduled_time}"
        )


def regular_event_handler(event: Event):
    print(f"Handled regular event at {datetime.now().isoformat()}")


@pytest.mark.asyncio
async def test_scheduled_events_are_processed():
    bus = MessageBus()
    await bus.start()

    # Register the handler for ScheduledEvent
    bus.register_event_handler(ScheduledEvent, scheduled_event_handler)

    # Schedule two events 10 seconds in the future
    scheduled_time = datetime.now() + timedelta(seconds=5)
    event1 = ScheduledEvent(scheduled_time=scheduled_time)
    event2 = ScheduledEvent(scheduled_time=scheduled_time)

    await bus.publish(event1)
    await bus.publish(event2)

    # Wait 11 seconds to ensure events are processed
    await asyncio.sleep(6)
    await bus.stop()


@pytest.mark.asyncio
async def test_scheduled_events_and_regular_events_are_processed():
    bus = MessageBus()
    await bus.start()

    # Register the handler for ScheduledEvent and regular events
    bus.register_event_handler(ScheduledEvent, scheduled_event_handler)
    bus.register_event_handler(Event, regular_event_handler)

    # Schedule two events 10 seconds in the future
    event1 = ScheduledEvent(scheduled_time=datetime.now() + timedelta(seconds=3))
    event2 = Event()
    event3 = ScheduledEvent(scheduled_time=datetime.now() + timedelta(seconds=5))
    event4 = Event()

    await bus.publish(event1)
    await bus.publish(event2)
    await bus.publish(event3)
    await bus.publish(event4)

    await asyncio.sleep(6)
    await bus.stop()


async def create_normal_event(bus: MessageBus) -> None:
    event = Event()
    await bus.publish(event)


async def create_scheduled_event(bus: MessageBus, scheduled_time: datetime) -> None:
    event = ScheduledEvent(scheduled_time=scheduled_time)
    await bus.publish(event)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test intentionally raises exception")
async def test_scheduled_events_with_exception():
    bus = MessageBus()
    bus_exception_hook(bus)
    await bus.start()

    # Register the handler for ScheduledEvent and regular events
    bus.register_event_handler(ScheduledEvent, scheduled_event_handler)
    bus.register_event_handler(Event, regular_event_handler)

    # Schedule two events 10 seconds in the future
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))

    await asyncio.sleep(3)
    await create_normal_event(bus)
    await create_normal_event(bus)
    await create_normal_event(bus)
    await create_normal_event(bus)
    await asyncio.sleep(1)
    await create_normal_event(bus)
    await create_normal_event(bus)

    # Raise an exception to test the excepthook
    raise RuntimeError("Test exception to trigger cleanup")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test intentionally calls sys.exit(1)")
async def test_scheduled_events_with_kill():
    bus = MessageBus()
    bus_exception_hook(bus)
    await bus.start()

    # Register the handler for ScheduledEvent and regular events
    bus.register_event_handler(ScheduledEvent, scheduled_event_handler)
    bus.register_event_handler(Event, regular_event_handler)

    # Schedule two events 10 seconds in the future
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))
    await create_scheduled_event(bus, datetime.now() + timedelta(seconds=10))

    await asyncio.sleep(3)
    await create_normal_event(bus)
    await create_normal_event(bus)
    await create_normal_event(bus)
    await create_normal_event(bus)
    await asyncio.sleep(10)
    await create_normal_event(bus)
    await create_normal_event(bus)

    # Raise an exception to test the excepthook
    sys.exit(1)


@pytest.mark.asyncio
async def test_base_bus_reloads_scheduled_events(monkeypatch):
    """Base bus should restore scheduled events on start (without requiring real DB)."""
    bus = MessageBus()
    await bus.reset()

    received = []

    async def collector(evt: Event):
        if isinstance(evt, ScheduledEvent):
            received.append(evt)

    bus.register_event_handler(ScheduledEvent, collector)

    # Monkeypatch the loader inside the bus module namespace
    from llmgine.bus import bus as bus_module
    events_to_load = [ScheduledEvent(scheduled_time=datetime.now() + timedelta(milliseconds=50))]
    monkeypatch.setattr(bus_module, "get_and_delete_unfinished_events", lambda: events_to_load)

    await bus.start()
    await asyncio.sleep(0.2)  # allow scheduled event to fire
    await bus.stop()
    await bus.reset()

    assert len(received) == 1


if __name__ == "__main__":
    asyncio.run(test_scheduled_events_with_kill())
