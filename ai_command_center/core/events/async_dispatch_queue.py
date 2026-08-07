"""Multi-pool async dispatch queue for EventBus R4b/R4c/R4d (Phase 5).

Pools match ``docs/plans/PHASE_5_ASYNC_EVENTBUS_PLAN.md`` §5.4 and
``ucgs.profiles/ai-command-center.yaml`` ``dispatch_policy.pools``.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

Handler = Callable[[Any], None]
InvokeFn = Callable[[Any, Handler | None], None]


@dataclass(frozen=True, slots=True)
class PoolConfig:
    """Configuration for one named worker pool."""

    name: str
    workers: int = 1
    queue_size: int = 100


DEFAULT_POOL_CONFIGS: tuple[PoolConfig, ...] = (
    PoolConfig(name="tool_execution", workers=1, queue_size=100),
    PoolConfig(name="workflow", workers=4, queue_size=50),
    PoolConfig(name="model", workers=2, queue_size=10),
)


@dataclass(frozen=True, slots=True)
class _DispatchJob:
    event: Any
    handler: Handler | None = None


class AsyncDispatchQueue:
    """Bounded multi-pool queue with graceful shutdown."""

    def __init__(
        self,
        *,
        invoke: InvokeFn,
        pools: tuple[PoolConfig, ...] | None = None,
    ) -> None:
        self._invoke = invoke
        configs = pools or DEFAULT_POOL_CONFIGS
        self._configs = {cfg.name: cfg for cfg in configs}
        self._queues: dict[str, queue.Queue[_DispatchJob | None]] = {}
        self._worker_counts: dict[str, int] = {}
        self._threads: list[threading.Thread] = []
        self._shutdown = threading.Event()
        self._depth = 0
        self._depth_lock = threading.Lock()
        self._dropped = 0
        self._start_workers()

    def _start_workers(self) -> None:
        for name, cfg in self._configs.items():
            maxsize = max(0, int(cfg.queue_size))
            q: queue.Queue[_DispatchJob | None] = queue.Queue(maxsize=maxsize)
            self._queues[name] = q
            workers = max(1, int(cfg.workers))
            self._worker_counts[name] = workers
            for index in range(workers):
                thread = threading.Thread(
                    target=self._worker_loop,
                    args=(name, q),
                    name=f"event-dispatch-{name}-{index}",
                    daemon=True,
                )
                thread.start()
                self._threads.append(thread)

    def _worker_loop(
        self,
        pool_name: str,
        work_queue: queue.Queue[_DispatchJob | None],
    ) -> None:
        while not self._shutdown.is_set():
            try:
                job = work_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if job is None:
                work_queue.task_done()
                break
            try:
                self._invoke(job.event, job.handler)
            except Exception:
                logger.exception(
                    "AsyncDispatchQueue worker failed pool=%s", pool_name
                )
            finally:
                with self._depth_lock:
                    self._depth = max(0, self._depth - 1)
                work_queue.task_done()

    @property
    def depth(self) -> int:
        with self._depth_lock:
            return self._depth

    @property
    def dropped(self) -> int:
        return self._dropped

    @property
    def pool_names(self) -> tuple[str, ...]:
        return tuple(self._configs)

    def pool_depth(self, name: str) -> int:
        work_queue = self._queues.get(name)
        return work_queue.qsize() if work_queue is not None else 0

    def enqueue(
        self,
        pool: str,
        event: Any,
        handler: Handler | None = None,
    ) -> bool:
        if self._shutdown.is_set():
            return False
        work_queue = self._queues.get(pool)
        if work_queue is None:
            raise KeyError(f"Unknown dispatch pool: {pool}")
        job = _DispatchJob(event=event, handler=handler)
        try:
            work_queue.put_nowait(job)
        except queue.Full:
            self._dropped += 1
            topic = getattr(event, "topic", "?")
            logger.warning(
                "AsyncDispatchQueue full; dropped event pool=%s topic=%s",
                pool,
                topic,
            )
            return False
        with self._depth_lock:
            self._depth += 1
        return True

    def shutdown(self, timeout: float = 5.0) -> None:
        self._shutdown.set()
        for name, work_queue in self._queues.items():
            sentinels = self._worker_counts.get(name, 1)
            for _ in range(sentinels):
                try:
                    work_queue.put_nowait(None)
                except queue.Full:
                    work_queue.put(None)
        deadline = timeout
        per_join = max(0.1, deadline / max(1, len(self._threads)))
        for thread in self._threads:
            thread.join(timeout=per_join)
        self._threads.clear()
        self._queues.clear()


__all__ = [
    "AsyncDispatchQueue",
    "DEFAULT_POOL_CONFIGS",
    "PoolConfig",
]
