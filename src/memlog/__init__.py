import asyncio
import contextlib
import functools
import os
import threading
import tracemalloc
from typing import Literal, Optional, Tuple, Set

from .model import Snapshot, KeyType
from .model import SnapshotMeta

_lock: threading.Lock = threading.Lock()
_first_snapshot: Snapshot | None = None
_current_snapshot: Snapshot | None = None
_do_snapshot_flag: Optional[bool] = None


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


def take_snapshot(title: str = None, top_k: Optional[int] = None,
                  filters: Optional[Set[str]] = None, ignores: Optional[Set[str]] = None,
                  ) -> Optional[Snapshot]:
    """
    Takes a memory snapshot using tracemalloc with optional filtering, ignoring, and metadata.

    This function captures the current state of the memory allocations and returns it as a
    Snapshot object. The snapshot metadata can be customized with a title, and the function
    supports including or excluding specific memory allocations based on the provided filters
    and ignore rules. The result can optionally include only the top `k` memory blocks.

    Args:
        title (str, optional): A descriptive title for the snapshot, used for metadata
            purposes. Defaults to None.
        top_k (Optional[int], optional): The number of top memory allocations to include
            in the snapshot. If None, all memory blocks are included. Defaults to None.
        filters (Optional[Set[str]], optional): A set of filters to include only specific
            memory allocations based on their origin. Defaults to None.
        ignores (Optional[Set[str]], optional): A set of patterns to ignore certain memory
            allocations from being included in the snapshot. Defaults to None.

    Returns:
        Optional[Snapshot]: Returns a `Snapshot` object containing the captured memory
            state and associated metadata. If the snapshot process fails or is disabled,
            None is returned.
    """
    if not _do_snapshot():
        return None
    with _lock:
        global _current_snapshot
        _current_snapshot = tracemalloc.take_snapshot()
        return Snapshot(snapshot=_current_snapshot, meta=SnapshotMeta(title=title),
                        filters=filters, ignores=ignores, top_k=top_k)


def snapshot(mode: Literal['first', 'start'] = 'start', title: str = None, top_k: Optional[int] = None,
             filters: Optional[Set[str]] = None, ignores: Optional[Set[str]] = None):
    """
    Creates a decorator that captures snapshots of the current state and optionally
    compares them after the decorated function executes. This is useful for tracking
    state changes before and after the function call, with customizable options for
    title, mode, and filters.

    Args:
        mode (Literal['first', 'start']): The snapshot mode. If 'first', uses an initial
            global snapshot as the reference point. If 'start', takes a new snapshot
            when the function starts.
        title (str, optional): A title to associate with the snapshots. Defaults to None.
        top_k (Optional[int], optional): The number of top differences to display during
            state comparison. Defaults to None (show all differences).
        filters (Optional[Set[str]], optional): A set of filters to apply when creating
            snapshots. Defaults to None (no filters applied).
        ignores (Optional[Set[str]], optional): A set of fields to ignore during state
            comparison. Defaults to None (compare all fields).

    Returns:
        Callable: A decorator that wraps the given function, capturing snapshots based
        on the provided parameters and comparing the state before and after the function
        execution.
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
                take_snapshot(title=title, filters=filters, ignores=ignores, top_k=top_k).compare_to(
                    start_snapshot).show()
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
                take_snapshot(title=title, filters=filters, ignores=ignores, top_k=top_k).compare_to(
                    start_snapshot).show()
            return res

        # 判断函数是否为异步函数
        if asyncio.iscoroutinefunction(func):
            return _async
        else:
            return _sync

    return _decorator


@contextlib.contextmanager
def snapshot_manager(mode: Literal['first', 'start'] = 'start', title: str = None, top_k: Optional[int] = None,
                     filters: Optional[Set[str]] = None, ignores: Optional[Set[str]] = None):
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
        take_snapshot(title=title, filters=filters, ignores=ignores, top_k=top_k).compare_to(start_snapshot).show()


if _do_snapshot():
    start()
