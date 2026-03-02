import asyncio
import contextlib
import functools
import os
import threading
import tracemalloc
from typing import Literal, Optional

from .model import Snapshot, KeyType
from .model import SnapshotMeta

_lock: threading.Lock = threading.Lock()
_first_snapshot: Snapshot | None = None
_current_snapshot: Snapshot | None = None
_do_snapshot_flag: bool = None


def _do_snapshot() -> bool:
    global _do_snapshot_flag
    if _do_snapshot_flag is None:
        _flag = os.environ.get('MEMLOG_ENABLE', None)
        if _flag is None:
            return False
        elif _flag == '1':
            _do_snapshot_flag = True
            return True
        else:
            _do_snapshot_flag = False
            return False
    else:
        return _do_snapshot_flag


def start() -> None:
    """
    Starts memory allocation tracking using tracemalloc and initializes the first snapshot.

    This function ensures that memory tracking begins only if the global lock is acquired successfully.
    If this is the first time the function is called, it records an initial memory allocation snapshot
    along with associated metadata.

    Raises:
        Exception: If the lock cannot be acquired or if another unexpected error occurs during execution.
    """
    if _do_snapshot():
        with _lock:
            tracemalloc.start()
            global _first_snapshot
            if _first_snapshot is None:
                _first_snapshot = Snapshot(tracemalloc.take_snapshot(), SnapshotMeta(title='First Snapshot'))


def get_first_snapshot() -> Optional[Snapshot]:
    """
    Retrieves the first snapshot in a thread-safe manner.

    This function ensures thread safety by utilizing a lock while retrieving
    the first snapshot. The snapshot returned represents the initial recorded
    state.

    Returns:
        Snapshot: The first snapshot instance.
    """
    with _lock:
        return _first_snapshot


def take_snapshot(title: str = None) -> Optional[Snapshot]:
    """
    Takes a snapshot of the current memory allocation state.

    This function captures the current state of memory allocations and wraps it
    in a Snapshot object. The snapshot can later be used for analysis, such as
    comparing memory usage over time or diagnosing memory leaks.

    Args:
        title: Optional descriptive title for the snapshot.

    Returns:
        Snapshot: An object representing the memory allocation snapshot.
    """
    if not _do_snapshot():
        return None
    with _lock:
        global _current_snapshot
        _current_snapshot = tracemalloc.take_snapshot()
        return Snapshot(_current_snapshot, SnapshotMeta(title=title))


def snapshot(mode: Literal['first', 'start'] = 'start', title: str = None, top_k: int = None):
    """
    A decorator that takes a snapshot before and after the execution of the given function.
    The decorator supports both synchronous and asynchronous functions.

    Returns:
        Callable: A wrapped function that invokes `take_snapshot` before and after its execution.
    """

    def _decorator(func):
        @functools.wraps(func)
        async def _async(*args, **kwargs):
            if _do_snapshot():
                if mode == 'first':
                    with _lock:
                        start_snapshot = get_first_snapshot()
                else:
                    start_snapshot = take_snapshot()
            res = await func(*args, **kwargs)
            if _do_snapshot():
                take_snapshot(title=title).compare_to(start_snapshot).show(top_k=top_k)
            return res

        @functools.wraps(func)
        def _sync(*args, **kwargs):
            if _do_snapshot():
                if mode == 'first':
                    with _lock:
                        start_snapshot = get_first_snapshot()
                else:
                    start_snapshot = take_snapshot()
            res = func(*args, **kwargs)
            if _do_snapshot():
                take_snapshot(title=title).compare_to(start_snapshot).show(top_k=top_k)
            return res

        # 判断函数是否为异步函数
        if asyncio.iscoroutinefunction(func):
            return _async
        else:
            return _sync

    return _decorator


@contextlib.contextmanager
def snapshot_manager(mode: Literal['first', 'start'] = 'start', title: str = None, top_k: int = None):
    """
    Context manager to manage and compare system snapshots.

    The function operates in one of two modes: 'first' or 'start'. In 'first' mode,
    it locks and retrieves the first available snapshot, while in 'start' mode,
    it captures a new snapshot at the beginning of the context. At the end of the
    context, it captures another snapshot and compares it to the initial one.
    The comparison result may optionally display the top differing items.

    Args:
        mode (Literal['first', 'start']): Determines the mode of snapshot operation.
            Use 'first' to lock and retrieve the first snapshot. Use 'start' to
            capture a new snapshot at the beginning.
        title (str, optional): The title to associate with the final snapshot
            taken at the end of the context.
        top_k (int, optional): The number of top differing items to display
            during the comparison.
    """
    if _do_snapshot():
        if mode == 'first':
            with _lock:
                start_snapshot = get_first_snapshot()
        else:
            start_snapshot = take_snapshot()
    yield
    if _do_snapshot():
        take_snapshot(title=title).compare_to(start_snapshot).show(top_k=top_k)


if _do_snapshot():
    start()
