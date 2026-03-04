# memlog

基于 `tracemalloc` 构建的轻量级、彩色 Python 内存分配追踪工具。

`memlog` 帮助您监控内存使用情况、识别潜在的内存泄漏，并在函数执行期间或特定上下文中比较内存快照。它在终端中提供清晰、格式化的表格输出。

[English](https://github.com/fjklqq/memlog/blob/main/README.md) | [中文](./README-ZH.md)

## 特性

- **环境变量控制激活**：仅在需要时通过环境变量启用追踪。
- **同步与异步支持**：无缝支持标准函数和 `async` 函数。
- **灵活的使用方式**：支持作为装饰器、上下文管理器或手动 API 使用。
- **过滤能力**：使用 `filters` 包含特定文件路径或模块（支持字符串列表或 `tracemalloc.Filter`）。
- **彩色输出**：以整洁、易读的表格格式显示内存统计信息和差异（自动检测 TTY 以启用彩色输出）。
- **比较模式**：将当前内存与基准（首次快照）或特定代码块的开始状态进行比较。

## 安装

```bash
pip install memlog
```

*(注意：所需依赖项：`click`、`datetime`、`humanfriendly` 和 `pydantic`。)*

## 配置

`memlog` 默认禁用以最小化开销。要启用内存追踪，请将 `MEMLOG_ENABLE` 环境变量设置为 `1`。

```bash
export MEMLOG_ENABLE=1
```

如果未设置 `MEMLOG_ENABLE` 或将其设置为其他任何值，`memlog` 函数将执行空操作（no-op）。

## 使用方法

### 1. 作为装饰器使用

轻松追踪特定函数的内存使用情况。

```python
import memlog

@memlog.snapshot(title="数据处理", top_k=5)
def process_data():
    # 在此处编写内存密集型代码
    data = [i for i in range(1000000)]
    return len(data)

# 调用时，它将打印一个显示内存变化的比较表
process_data()
```

装饰器也支持 `async` 函数：

```python
@memlog.snapshot(title="异步任务")
async def run_task():
    await asyncio.sleep(1)
```

### 2. 作为上下文管理器使用

在特定代码块内追踪内存。

```python
import memlog

with memlog.snapshot_manager(title="代码块比较", top_k=3):
    temp_list = [str(i) for i in range(50000)]
    # 退出代码块时将打印比较表
```

### 3. 手动获取快照

如需更精细的控制，可使用手动 API。

```python
import memlog

# 开始追踪（如果 MEMLOG_ENABLE=1，则会自动调用）
memlog.start()

# 获取初始快照
s1 = memlog.take_snapshot("初始状态")

# ... 运行一些代码 ...

# 获取另一个快照并进行比较
s2 = memlog.take_snapshot("操作后")
s2.compare_to(s1).show(top_k=10)
```

## API 参考

### 核心函数

- `memlog.start()`：初始化 `tracemalloc` 并记录“首次快照”。
- `memlog.take_snapshot(title=None, filters=None)`：捕获当前的内存状态。
    - `filters`：要在追踪中包含的字符串列表或 `tracemalloc.Filter` 对象（例如 `["src/memlog"]`）。
- `memlog.get_first_snapshot()`：返回在 `memlog` 启动时拍摄的第一个快照。
- `memlog.snapshot(mode='start', title=None, filters=None, top_k=10, key_type=KeyType.TRACEBACK)`：用于函数的装饰器。
    - `mode='start'`：将结束状态与函数开始前的状态进行比较。
    - `mode='first'`：将结束状态与全局“首次快照”进行比较。
- `memlog.snapshot_manager(mode='start', title=None, filters=None, top_k=10, key_type=KeyType.TRACEBACK)`：上下文管理器。

### 快照方法 (Snapshot Methods)

- `snapshot.compare_to(other_snapshot, key_type=KeyType.TRACEBACK, cumulative=False)`：返回两个快照之间的比较对象。
- `snapshot.compare(key_type=KeyType.TRACEBACK, cumulative=False)`：将当前快照与全局“首次快照”进行比较。
- `snapshot.statistics(key_type=KeyType.TRACEBACK, cumulative=False)`：返回快照的统计信息。
- `snapshot.dump(filename)`：将快照保存到文件。
- `snapshot.load(filename)`：从文件加载快照。

### 统计方法 (Statistics Methods)

- `statistics.show(top_k=10)`：将格式化后的统计信息打印到标准输出。
- `statistics.show_table(top_k=10)`：将格式化后的表格打印到标准输出。

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。
