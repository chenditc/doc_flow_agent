"""Utilities for managing trace streaming connections and remote syncing."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class TraceStreamManager:
    """Coordinates SSE connections, orchestrator sync polling, and broadcasts."""

    def __init__(
        self,
        *,
        orchestrator_base_url: str,
        sync_timeout: float,
        poll_interval: float,
        debounce_seconds: float = 0.3,
    ):
        self._orchestrator_base = orchestrator_base_url.rstrip("/") if orchestrator_base_url else ""
        self._sync_timeout = sync_timeout
        self._poll_interval = poll_interval
        self._debounce_seconds = debounce_seconds

        self._active_connections: Dict[str, List[asyncio.Queue]] = {}
        self._pending_broadcasts: Dict[str, asyncio.TimerHandle] = {}
        self._trace_sync_tasks: Dict[str, asyncio.Task] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Attach the asyncio loop used for scheduling broadcasts."""
        self._loop = loop

    def detach_loop(self) -> None:
        """Detach the stored loop (typically on shutdown)."""
        self._loop = None

    def notify_file_modified(self, trace_id: str) -> None:
        """Called from watchdog thread when a trace file changes."""
        if not self._loop:
            logger.warning("TraceStreamManager has no loop; skipping broadcast for %s", trace_id)
            return
        try:
            self._loop.call_soon_threadsafe(self._schedule_broadcast, trace_id)
        except Exception as exc:
            logger.error("Failed to schedule broadcast for %s: %s", trace_id, exc)

    def _schedule_broadcast(self, trace_id: str) -> None:
        loop = asyncio.get_running_loop()
        handle = self._pending_broadcasts.get(trace_id)
        if handle and not handle.cancelled():
            handle.cancel()
        self._pending_broadcasts[trace_id] = loop.call_later(
            self._debounce_seconds, self._broadcast_update, trace_id
        )

    def _broadcast_update(self, trace_id: str) -> None:
        handle = self._pending_broadcasts.pop(trace_id, None)
        if handle and not handle.cancelled():
            # Nothing else required; removal ensures next update can schedule a new handle.
            pass

        queues = self._active_connections.get(trace_id, [])
        if not queues:
            return
        message = {
            "event": "file_updated",
            "trace_id": trace_id,
            "timestamp": time.time(),
        }
        logger.info("Sending SSE message to %d connections for %s", len(queues), trace_id)
        for queue in list(queues):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Queue full for trace %s; dropping message", trace_id)
            except Exception as exc:
                logger.error("Failed pushing SSE message for %s: %s", trace_id, exc)

    def register_connection(self, trace_id: str) -> asyncio.Queue:
        """Create and register a queue for a new SSE client."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._active_connections.setdefault(trace_id, []).append(queue)
        logger.info(
            "Registered SSE connection for %s (total=%d)",
            trace_id,
            len(self._active_connections[trace_id]),
        )
        return queue

    def unregister_connection(self, trace_id: str, queue: asyncio.Queue) -> None:
        """Remove a queue when the SSE client disconnects."""
        queues = self._active_connections.get(trace_id)
        if not queues:
            return
        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._active_connections.pop(trace_id, None)
            self._stop_sync_task_if_inactive(trace_id)

    async def request_sync_once(self, trace_id: str, *, force: bool = False) -> Optional[Dict[str, Any]]:
        """Ask the orchestrator to refresh a trace immediately and return response metadata."""
        if not self._orchestrator_base:
            return None
        url = f"{self._orchestrator_base}/traces/{trace_id}/sync"
        params = {"force": "true"} if force else None
        try:
            async with httpx.AsyncClient(timeout=self._sync_timeout) as client:
                response = await client.post(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.debug("Trace sync request failed for %s: %s", trace_id, exc)
            return None

    def ensure_sync_polling(self, trace_id: str) -> None:
        """Start periodic sync while there are active SSE listeners."""
        if not self._orchestrator_base:
            return
        existing = self._trace_sync_tasks.get(trace_id)
        if existing and not existing.done():
            return
        loop = asyncio.get_running_loop()
        self._trace_sync_tasks[trace_id] = loop.create_task(self._poll_loop(trace_id))

    async def _poll_loop(self, trace_id: str):
        try:
            while True:
                if not self._active_connections.get(trace_id):
                    break
                info = await self.request_sync_once(trace_id, force=True)
                if info and info.get("is_terminal"):
                    logger.info("Trace %s is terminal; stopping sync polling", trace_id)
                    break
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            raise
        finally:
            self._trace_sync_tasks.pop(trace_id, None)

    def _stop_sync_task_if_inactive(self, trace_id: str) -> None:
        task = self._trace_sync_tasks.get(trace_id)
        if not task:
            return
        if self._active_connections.get(trace_id):
            return
        if not task.done():
            task.cancel()
        self._trace_sync_tasks.pop(trace_id, None)

    async def shutdown(self) -> None:
        """Gracefully stop all background tasks and clear state."""
        for trace_id, handle in list(self._pending_broadcasts.items()):
            try:
                if handle and not handle.cancelled():
                    handle.cancel()
            except Exception:
                pass
        self._pending_broadcasts.clear()

        if self._trace_sync_tasks:
            for task in self._trace_sync_tasks.values():
                task.cancel()
            await asyncio.gather(*self._trace_sync_tasks.values(), return_exceptions=True)
            self._trace_sync_tasks.clear()

        self._active_connections.clear()
        self._loop = None

    def connection_count(self, trace_id: str) -> int:
        return len(self._active_connections.get(trace_id, []))

    def active_trace_ids(self) -> List[str]:
        return list(self._active_connections.keys())

    def connection_debug_snapshot(self) -> Dict[str, Dict[str, Any]]:
        snapshot: Dict[str, Dict[str, Any]] = {}
        for tid, queues in self._active_connections.items():
            try:
                q_sizes = [q.qsize() for q in queues]
            except Exception:
                q_sizes = [None for _ in queues]
            snapshot[tid] = {
                "connections": len(queues),
                "queue_sizes": q_sizes,
            }
        return snapshot

    def pending_broadcast_traces(self) -> List[str]:
        return list(self._pending_broadcasts.keys())
