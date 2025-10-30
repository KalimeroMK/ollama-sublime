from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from queue import PriorityQueue
from typing import Callable, Any, Dict, Optional, Tuple


class _Task:
    __slots__ = ("priority", "seq", "key", "fn", "args", "kwargs")

    def __init__(self, priority: int, seq: int, key: Optional[str], fn: Callable, args: tuple, kwargs: dict):
        self.priority = priority
        self.seq = seq
        self.key = key
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def __lt__(self, other: "_Task"):
        # lower priority value comes first, then FIFO by seq
        return (self.priority, self.seq) < (other.priority, other.seq)


class WorkerManager:
    """
    Shared worker manager with a single ThreadPoolExecutor and a priority queue.
    - Coalesces tasks with the same key (returns the in-flight Future)
    - Simple priorities: 0 (high), 1 (normal), 2 (low)
    """

    def __init__(self, max_workers: int = 8):
        self._executor = ThreadPoolExecutor(max_workers=max_workers or 4, thread_name_prefix="LWAI")
        self._queue: PriorityQueue[_Task] = PriorityQueue()
        self._inflight: Dict[str, Future] = {}
        self._seq = 0
        self._lock = threading.Lock()
        self._dispatcher_started = False

    def submit(self, fn: Callable[..., Any], *args, priority: int = 1, key: Optional[str] = None, **kwargs) -> Future:
        with self._lock:
            if key and key in self._inflight:
                return self._inflight[key]
            self._seq += 1
            task = _Task(priority=priority, seq=self._seq, key=key, fn=fn, args=args, kwargs=kwargs)
            fut: Future = Future()
            if key:
                self._inflight[key] = fut
            self._queue.put(task)
            self._ensure_dispatcher()
            return fut

    def _ensure_dispatcher(self):
        if self._dispatcher_started:
            return
        self._dispatcher_started = True
        threading.Thread(target=self._dispatch_loop, name="LWAI-Dispatcher", daemon=True).start()

    def _dispatch_loop(self):
        while True:
            task: _Task = self._queue.get()
            # schedule on executor and wire completion to our Future + inflight cleanup
            outer_future: Future
            with self._lock:
                outer_future = self._inflight.get(task.key) if task.key else None
            inner_future = self._executor.submit(task.fn, *task.args, **task.kwargs)

            def _on_done(_inner: Future, _task: _Task, _outer: Optional[Future]):
                try:
                    res = _inner.result()
                    if _outer is not None and not _outer.done():
                        _outer.set_result(res)
                except BaseException as e:  # propagate exceptions
                    if _outer is not None and not _outer.done():
                        _outer.set_exception(e)
                finally:
                    if _task.key:
                        with self._lock:
                            self._inflight.pop(_task.key, None)
            inner_future.add_done_callback(lambda f, t=task, o=outer_future: _on_done(f, t, o))


_singleton: Optional[WorkerManager] = None
_singleton_lock = threading.Lock()


def get_worker_manager(max_workers: int = 8) -> WorkerManager:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = WorkerManager(max_workers=max_workers)
    return _singleton
