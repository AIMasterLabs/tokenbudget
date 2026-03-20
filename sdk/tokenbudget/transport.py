# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""TokenBudget event transport — async batched delivery to the TokenBudget API."""
from __future__ import annotations

import dataclasses
import logging
import queue
import threading
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from tokenbudget.config import TokenBudgetConfig
    from tokenbudget.types import UsageEvent

logger = logging.getLogger(__name__)


def _event_to_dict(event: "UsageEvent") -> dict:
    """Serialize a UsageEvent to a JSON-serializable dict."""
    return dataclasses.asdict(event)


class EventTransport:
    """Thread-safe event transport with background flushing."""

    def __init__(self, config: "TokenBudgetConfig") -> None:
        self.config = config
        self.queue: queue.Queue["UsageEvent"] = queue.Queue(maxsize=config.max_queue_size)
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        self._lock = threading.Lock()
        self._flush_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._start_flush_thread()

    def _start_flush_thread(self) -> None:
        """Start the background flush thread if not already running."""
        with self._lock:
            if self._flush_thread is None or not self._flush_thread.is_alive():
                self._flush_thread = threading.Thread(
                    target=self._flush_loop,
                    daemon=True,
                    name="tokenbudget-flush",
                )
                self._flush_thread.start()

    def _flush_loop(self) -> None:
        """Background loop: flush every flush_interval seconds."""
        while not self._stop_event.wait(timeout=self.config.flush_interval):
            self._do_flush()

    def send(self, event: "UsageEvent") -> None:
        """Enqueue an event. Never blocks, never raises."""
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            logger.warning("TokenBudget event queue is full; dropping event.")
        except Exception as exc:
            logger.warning("TokenBudget: failed to enqueue event: %s", exc)

    def flush_sync(self) -> None:
        """Drain the queue and POST all events to the API endpoint."""
        self._do_flush()

    def _do_flush(self) -> None:
        """Internal flush implementation."""
        if self.queue.empty():
            return

        # Drain the queue into a local list
        events: list["UsageEvent"] = []
        while True:
            try:
                events.append(self.queue.get_nowait())
            except queue.Empty:
                break

        if not events:
            return

        url = f"{self.config.endpoint}/v1/events/batch"
        payload = {"events": [_event_to_dict(e) for e in events]}

        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("TokenBudget: flush failed (%s); re-queuing %d events.", exc, len(events))
            # Re-queue events for retry on next flush
            for event in events:
                try:
                    self.queue.put_nowait(event)
                except queue.Full:
                    logger.warning("TokenBudget: queue full during re-queue; dropping event.")

    def shutdown(self) -> None:
        """Stop the flush thread, flush remaining events, and close the HTTP client."""
        self._stop_event.set()
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)
        self._do_flush()
        try:
            self._client.close()
        except Exception:
            pass
