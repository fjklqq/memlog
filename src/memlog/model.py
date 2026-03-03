# File: snapshot.py
# Date: 2026/2/27
# Desc:
import datetime
import linecache
import logging
import pickle
import sys
import tracemalloc
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union


from humanfriendly import format_size

from .colorful import (
    colorful_title, colorful_head,
    colorful_traceback, colorful_size, colorful_count, colorful_size_diff, colorful
)
from .enums import KeyType, StyleColor

FiltersTypes = Optional[Union[Sequence[Union[tracemalloc.DomainFilter, tracemalloc.Filter]], Sequence[str]]]


@dataclass
class SnapshotMeta:
    datetime_at: datetime.datetime
    title: str

    def __init__(self, datetime_at: datetime.datetime = None, title: Optional[str] = None):
        self.datetime_at = datetime_at if datetime_at else datetime.datetime.now()
        self.title = title or "Snapshot"

    @property
    def title_with_datetime(self):
        return f"{self.title} at {self.datetime_at.strftime('%Y-%m-%d %H:%M:%S')}"


class StatisticsMinx:
    _column: List[str]
    _statistic: List[tracemalloc.Statistic | tracemalloc.StatisticDiff]
    _meta: SnapshotMeta

    @property
    def meta(self) -> SnapshotMeta:
        return self._meta

    @staticmethod
    def _find_row_length(columns: List[str], rows: List[List[str]]) -> List[int]:
        if len(rows):
            lengths = [max(map(lambda x: len(str(x[i])), rows)) for i in range(len(rows[0]))]
        else:
            lengths = [0 for _ in columns]
        return [max(i, len(j)) + 1 for i, j in zip(lengths, columns)]

    @staticmethod
    def _format_column(columns: List[str], length: List[int]) -> List[str]:
        return [str(c).center(l) for c, l in zip(columns, length)]

    @staticmethod
    def _format_row(row: List[str], length: List[int]):
        raise NotImplementedError

    def _colorful_column(self) -> List[str]:
        return [colorful_head(str(c)) for c in self._column]

    @staticmethod
    def _colorful_row(row: List[str]) -> List[str]:
        raise NotImplementedError

    @staticmethod
    def _parser(statistic: tracemalloc.Statistic | tracemalloc.StatisticDiff):
        raise NotImplementedError

    @staticmethod
    def _table_border(length: List[int], sep='', color=False):
        return sep.join(['━'.center((l - 14) if color else l, '━') for l in length])

    def __str__(self) -> str:
        statistics_info = [self._parser(statistic) for statistic in self._statistic]
        return repr(statistics_info)

    def show(self, top_k: Optional[int] = 10, **kwargs) -> None:
        color = sys.stdout.isatty()
        result = "\n"
        if color:
            title = colorful_title(self._meta.title_with_datetime)
        else:
            title = self._meta.title_with_datetime
        result += f">>> {title}\n"
        for statistic in self._statistic[:top_k]:
            _row = self._parser(statistic)
            _column = self._column
            _sep = ': '
            if color:
                _row = self._colorful_row(_row)
                _column = self._colorful_column()
                _sep = colorful(_sep, bold=True)
            result += '  '.join(
                [f"{name}{_sep}{value}" for name, value in zip(_column[1:], _row[1:])]
            ) + '\n'

            for frame in statistic.traceback:
                line = f'  File "{frame.filename}", line {frame.lineno}\n'
                _code = linecache.getline(frame.filename, frame.lineno).strip()
                if _code:
                    if color:
                        line = colorful(line, bold=True)
                        line += f'    {colorful(_code, fg=StyleColor.RED)}\n'
                    else:
                        line += f'    {_code}\n'

                result += line
            result += '\n'
        logging.warning(result, stacklevel=4)

    def show_table(self, top_k: Optional[int] = 10, **kwargs) -> None:
        color = sys.stdout.isatty()
        statistics_info = [self._parser(statistic) for statistic in self._statistic[:top_k]]
        if color:
            statistics_info = list(map(self._colorful_row, statistics_info))
            columns = self._colorful_column()
            title = colorful_title(self._meta.title_with_datetime)
        else:
            columns = self._column
            title = self._meta.title_with_datetime
        length = self._find_row_length(columns, statistics_info)
        columns = ' ┃ '.join(self._format_column(columns, length))

        rows = [' ┃ '.join(self._format_row(info, length)) for info in statistics_info]
        _sep = ' ┃\n┃ '

        _result_str = (
            f">>> {title}\n"
            f"┏━{self._table_border(length, sep='━┳━', color=color)}━┓\n"
            f"┃ {columns} ┃\n"
            f"┣━{self._table_border(length, sep='━╋━', color=color)}━┫\n"
        )
        if rows:
            _result_str += f"┃ {_sep.join(rows)} ┃\n"
        _result_str += f"┗━{self._table_border(length, sep='━┻━', color=color)}━┛\n"
        logging.warning(_result_str, stacklevel=4)


class Statistics(StatisticsMinx):
    def __init__(self, statistics: List[tracemalloc.Statistic], meta: SnapshotMeta) -> None:
        self._statistic = statistics
        self._meta = meta
        self._column = ['Traceback', 'Size', 'Count']

    def __len__(self):
        return len(self._statistic)

    @staticmethod
    def _format_row(row, length, ):
        return [
            str(row[0]).ljust(length[0]),
            str(row[1]).rjust(length[1]),
            str(row[2]).rjust(length[2]),
        ]

    @staticmethod
    def _colorful_row(row) -> List[str]:
        return [
            colorful_traceback(row[0]),
            colorful_size(row[1]),
            colorful_count(row[2]),
        ]

    @staticmethod
    def _parser(statistic: tracemalloc.Statistic):
        return statistic.traceback, format_size(statistic.size), statistic.count


class StatisticsDiff(StatisticsMinx):
    def __init__(self, statistics: List[tracemalloc.StatisticDiff], meta: SnapshotMeta) -> None:
        self._statistic = statistics
        self._meta = meta
        self._column = ['Traceback', 'Size', 'Count', 'Size Diff']

    @staticmethod
    def _format_row(row, length, ):
        return [
            str(row[0]).ljust(length[0]),
            str(row[1]).rjust(length[1]),
            str(row[2]).rjust(length[2]),
            str(row[3]).rjust(length[3]),
        ]

    @staticmethod
    def _colorful_row(row) -> List[str]:
        return [
            colorful_traceback(row[0]),
            colorful_size(row[1]),
            colorful_count(row[2]),
            colorful_size_diff(row[3]),
        ]

    @staticmethod
    def _parser(statistic: tracemalloc.StatisticDiff):
        return statistic.traceback, format_size(statistic.size), statistic.count, format_size(statistic.size_diff)


class Snapshot:
    def __init__(self, snapshot: tracemalloc.Snapshot, meta: SnapshotMeta, filters: FiltersTypes = None) -> None:
        self._meta = meta
        if filters:
            _filters = []
            for f in filters:
                if isinstance(f, str):
                    _filters.append(tracemalloc.Filter(True, f))
                else:
                    _filters.append(f)
            self._snapshot = snapshot.filter_traces(_filters)

        else:
            self._snapshot = snapshot

    @property
    def meta(self) -> SnapshotMeta:
        return self._meta

    def __str__(self) -> str:
        return f"Snapshot(meta={self._meta})"

    @property
    def snapshot(self) -> tracemalloc.Snapshot:
        return self._snapshot

    def dump(self, filename):
        with open(filename, "wb") as fp:
            pickle.dump(self, fp, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(filename):
        with open(filename, "rb") as fp:
            return pickle.load(fp)

    def statistics(self, key_type: KeyType = KeyType.TRACEBACK, cumulative=False) -> Statistics:
        return Statistics(
            statistics=self._snapshot.statistics(key_type.value, cumulative=cumulative),
            meta=self._meta
        )

    def compare(self, key_type: KeyType = KeyType.TRACEBACK, cumulative=False) -> StatisticsDiff:
        from memlog import get_first_snapshot

        return StatisticsDiff(
            statistics=self._snapshot.compare_to(get_first_snapshot().snapshot, key_type.value, cumulative=cumulative),
            meta=self._meta
        )

    def compare_to(self, other: 'Snapshot', key_type: KeyType = KeyType.TRACEBACK, cumulative=False) -> StatisticsDiff:
        return StatisticsDiff(
            statistics=self._snapshot.compare_to(other.snapshot, key_type.value, cumulative=cumulative),
            meta=self._meta,
        )
