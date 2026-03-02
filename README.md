# memlog

A lightweight and colorful Python memory allocation tracking tool built on top of `tracemalloc`.

`memlog` helps you monitor memory usage, identify potential memory leaks, and compare memory snapshots during function execution or within a specific context. It provides clear, formatted table output in your terminal.

[English](./README.md) | [中文](./README-ZH.md)

## Features

- **Environment-controlled activation**: Enable tracking only when needed using an environment variable.
- **Synchronous & Asynchronous Support**: Works seamlessly with both standard and `async` functions.
- **Flexible Usage**: Use as a decorator, context manager, or manual API.
- **Filtering Capabilities**: Include or exclude specific file paths or modules using `filters` and `ignores`.
- **Colorful Output**: Displays memory statistics and differences in a clean, readable table format.
- **Comparison Modes**: Compare current memory against a baseline (first snapshot) or the start of a specific block.

## Installation

```bash
pip install memlog
```

*(Note: Ensure you have the required dependencies: `click`, `humanfriendly`, and `pydantic`.)*

## Configuration

`memlog` is disabled by default to minimize overhead. To enable memory tracking, set the `MEMLOG_ENABLE` environment variable to `1`.

```bash
export MEMLOG_ENABLE=1
```

If `MEMLOG_ENABLE` is not set or set to any other value, `memlog` functions will perform no-op operations.

## Usage

### 1. Using as a Decorator

Easily track memory usage of a specific function.

```python
import memlog

@memlog.snapshot(title="Data Processing", top_k=5)
def process_data():
    # Your memory-intensive code here
    data = [i for i in range(1000000)]
    return len(data)

# When called, it will print a comparison table showing memory changes
process_data()
```

The decorator also supports `async` functions:

```python
@memlog.snapshot(title="Async Task")
async def run_task():
    await asyncio.sleep(1)
```

### 2. Using as a Context Manager

Track memory within a specific block of code.

```python
import memlog

with memlog.snapshot_manager(title="Block Comparison", top_k=3):
    temp_list = [str(i) for i in range(50000)]
    # Comparison table is printed when exiting the block
```

### 3. Manual Snapshotting

For more granular control, use the manual API.

```python
import memlog

# Start tracking (automatically called if MEMLOG_ENABLE=1)
memlog.start()

# Take an initial snapshot
s1 = memlog.take_snapshot("Initial State")

# ... run some code ...

# Take another snapshot and compare
s2 = memlog.take_snapshot("After Operation")
s2.compare_to(s1).show(top_k=10)
```

## API Reference

### Core Functions

- `memlog.start()`: Initializes `tracemalloc` and records the "First Snapshot".
- `memlog.take_snapshot(title=None, top_k=None, filters=None, ignores=None)`: Captures the current memory state.
    - `filters`: A set of strings to include in the traceback (e.g., `{"src/memlog"}`).
    - `ignores`: A set of strings to exclude from the traceback.
- `memlog.get_first_snapshot()`: Returns the very first snapshot taken when `memlog` was started.
- `memlog.snapshot(mode='start', title=None, top_k=None, filters=None, ignores=None)`: A decorator for functions.
    - `mode='start'`: Compares the end state to the state just before the function started.
    - `mode='first'`: Compares the end state to the global "First Snapshot".
- `memlog.snapshot_manager(mode='start', title=None, top_k=None, filters=None, ignores=None)`: A context manager.

### Snapshot Methods

- `snapshot.compare_to(other_snapshot, key_type=KeyType.TRACEBACK, cumulative=False)`: Returns a comparison object between two snapshots.
- `snapshot.compare(key_type=KeyType.TRACEBACK, cumulative=False)`: Compares current snapshot to the global "First Snapshot".
- `snapshot.statistics(key_type=KeyType.TRACEBACK, cumulative=False)`: Returns statistics for the snapshot.
- `snapshot.dump(filename)`: Save snapshot to a file.
- `snapshot.load(filename)`: Load snapshot from a file.

### Statistics Methods

- `statistics.show(top_k=None)`: Prints the formatted table to stdout.

## License

(Specify your license here, e.g., MIT)
