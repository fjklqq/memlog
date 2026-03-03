import asyncio
import contextlib
import functools
import os
import threading
import tracemalloc
from typing import Literal, Optional, Tuple, Set

from .model import Snapshot, KeyType, SnapshotMeta, FiltersTypes

_first_snapshot: Snapshot | None = None
_current_snapshot: Snapshot | None = None
_do_snapshot_flag: Optional[bool] = None


def _do_snapshot(without_is_tracing: bool = True) -> bool:
    global _do_snapshot_flag
    if _do_snapshot_flag is None:
        _flag = os.environ.get('MEMLOG_ENABLE', None)
        if _flag is None:
            return False
        elif _flag == '1':
            if not without_is_tracing:
                if tracemalloc.is_tracing():
                    _do_snapshot_flag = True
                    return True
                else:
                    _do_snapshot_flag = False
                    return False
            _do_snapshot_flag = True
            return True
        else:
            _do_snapshot_flag = False
            return False
    else:
        return _do_snapshot_flag


def get_first_snapshot() -> Optional[Snapshot]:
    return _first_snapshot


def _set_first_snapshot(snapshot: Snapshot) -> Optional[Snapshot]:
    global _first_snapshot
    if _first_snapshot is None:
        _first_snapshot = snapshot
    return snapshot


def _clear_first_snapshot() -> None:
    global _first_snapshot
    _first_snapshot = None


def _set_current_snapshot(snapshot: Snapshot) -> Optional[Snapshot]:
    global _current_snapshot
    if _current_snapshot is None:
        _current_snapshot = snapshot
    return snapshot


def _clear_current_snapshot() -> None:
    global _current_snapshot
    _current_snapshot = None


def get_current_snapshot() -> Optional[Snapshot]:
    global _current_snapshot
    return _current_snapshot


def start() -> None:
    """
    Starts memory allocation tracking using tracemalloc and initializes the first snapshot.

    This function ensures that memory tracking begins only if the global lock is acquired successfully.
    If this is the first time the function is called, it records an initial memory allocation snapshot
    along with associated metadata.

    Raises:
        Exception: If the lock cannot be acquired or if another unexpected error occurs during execution.
    """
    if _do_snapshot(without_is_tracing=False):
        tracemalloc.start()
        _set_first_snapshot(Snapshot(tracemalloc.take_snapshot(), SnapshotMeta(title='First Snapshot')))


def stop():
    if _do_snapshot(without_is_tracing=False):
        tracemalloc.stop()
        _clear_first_snapshot()
        _clear_current_snapshot()
        tracemalloc.clear_traces()


def clear():
    if _do_snapshot(without_is_tracing=False):
        tracemalloc.clear_traces()
        _clear_first_snapshot()
        _clear_current_snapshot()


def take_snapshot(title: str = None, filters: FiltersTypes = None) -> Optional[Snapshot]:
    """
    Takes a snapshot of the current state and stores it with optional metadata and filters.

    This function creates a snapshot of the current memory usage using the `tracemalloc` module.
    The snapshot can be associated with a title and filters for metadata purposes. If the snapshot
    could not be taken, it returns None.

    Args:
        title (str, optional): A title or description for the snapshot.
        filters (FiltersTypes, optional): Filters to be applied to the snapshot.

    Returns:
        Optional[Snapshot]: The created snapshot object if successful, otherwise None.
    """
    if not _do_snapshot():
        return None

    return _set_current_snapshot(
        Snapshot(snapshot=tracemalloc.take_snapshot(),
                 meta=SnapshotMeta(title=title), filters=filters)
    )


def snapshot(mode: Literal['first', 'start'] = 'start', title: str = None, filters: FiltersTypes = None,
             top_k: Optional[int] = 10, key_type: KeyType = KeyType.TRACEBACK):
    """
    Decorator function to create and manage snapshots during function execution. A snapshot captures
    certain aspects of the program state for analysis purposes. The decorator works with both synchronous
    and asynchronous functions.

    Args:
        mode (Literal['first', 'start']): The mode of the snapshot. If 'start', it always takes a new
            starting snapshot. If 'first', it uses the first snapshot taken during the process.
        title (str): An optional title for the snapshot. Defaults to the function's qualified name.
        filters (FiltersTypes): Filters to apply when taking the snapshot. Can be used to customize
            captured data.
        top_k (Optional[int]): The maximum number of top differences to display. Defaults to 10.
        key_type (KeyType): The type of keys used for comparison between snapshots. Typically determines
            the method of analyzing differences.

    Returns:
        Callable: A decorator function that wraps the given function to handle snapshots.

    """

    def _decorator(func):
        _title = title or f"Snapshot[{func.__qualname__}]"

        @functools.wraps(func)
        async def _async(*args, **kwargs):
            if _do_snapshot():
                start_snapshot = get_first_snapshot()
                if mode == 'start' or start_snapshot is None:
                    start_snapshot = _set_current_snapshot(take_snapshot(title=_title + '[START]'))
            res = await func(*args, **kwargs)
            if _do_snapshot():
                _set_current_snapshot(take_snapshot(_title, filters)).compare_to(start_snapshot, key_type).show(
                    top_k=top_k)
            return res

        @functools.wraps(func)
        def _sync(*args, **kwargs):
            if _do_snapshot():
                start_snapshot = get_first_snapshot()
                if mode == 'start' or start_snapshot is None:
                    start_snapshot = _set_current_snapshot(take_snapshot(title=_title + '[START]'))
            res = func(*args, **kwargs)
            if _do_snapshot():
                _set_current_snapshot(take_snapshot(_title, filters)).compare_to(start_snapshot, key_type).show(
                    top_k=top_k)
            return res

        # 判断函数是否为异步函数
        if asyncio.iscoroutinefunction(func):
            return _async
        else:
            return _sync

    return _decorator


@contextlib.contextmanager
def snapshot_manager(mode: Literal['first', 'start'] = 'start', title: str = None, filters: FiltersTypes = None,
                     top_k: Optional[int] = 10, key_type: KeyType = KeyType.TRACEBACK):
    """
    Manages memory snapshots within a context to identify and analyze memory usage patterns.

    This context manager facilitates the creation and comparison of memory snapshots to help
    detect memory-related issues. It captures an initial memory snapshot when entering the
    context and compares it to a subsequent snapshot taken upon exiting the context. The
    comparison identifies differences in memory allocation based on the specified filters
    and settings.

    Args:
        mode (Literal['first', 'start']): Determines the behavior for selecting the starting
            snapshot. 'start' forces the creation of a new snapshot on entry, while 'first'
            uses the first available snapshot, if existing.
        title (str, optional): A label for the captured snapshots, helpful for identification
            in the reports.
        filters (FiltersTypes, optional): Criteria to filter objects included in memory
            snapshots, such as specifying which objects to include or exclude.
        top_k (Optional[int]): Limits the number of differences or memory-hogging entries
            displayed in the report to this number. Defaults to 10.
        key_type (KeyType): Determines the basis for comparing snapshots, typically by
            traceback identifiers.

    Yields:
        None: This context manager does not return any value but performs its operations
            on entry and exit.
    """

    if _do_snapshot():
        start_snapshot = get_first_snapshot()
        if mode == 'start' or start_snapshot is None:
            start_snapshot = _set_current_snapshot(take_snapshot(title=title))
    yield
    if _do_snapshot():
        _set_current_snapshot(take_snapshot(title, filters)).compare_to(start_snapshot, key_type).show(top_k=top_k)


if _do_snapshot():
    start()
