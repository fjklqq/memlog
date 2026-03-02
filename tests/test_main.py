# File: test_main.py
# Date: 2026/3/2
# Desc:
import os

os.environ['MEMLOG_ENABLE'] = '1'
import unittest

import memlog

import logging

logging.basicConfig(level=logging.WARNING, format='%(asctime)s "%(pathname)s:%(lineno)s" - %(message)s')
logger = logging.getLogger(__name__)


class TestMain(unittest.TestCase):
    def test_get_first_snapshot(self):
        s = memlog.get_first_snapshot()
        assert isinstance(s, memlog.Snapshot)
        assert s.snapshot is not None
        assert s.meta.title == 'First Snapshot'

    def test_take_snapshot(self):
        s = memlog.take_snapshot(filters={'unittest', }, top_k=1)
        assert isinstance(s, memlog.Snapshot)
        assert s.snapshot is not None
        assert s.meta.title == 'Snapshot'
        assert len(s.statistics()) > 0
        s.statistics().show()

    def test_snapshot(self):
        @memlog.snapshot(top_k=1, title='test', filters={'unittest', })
        def test_func():
            return 1 + 1

        _ = test_func()

    def test_snapshot_manager(self):
        with memlog.snapshot_manager(top_k=1, title='test', filters={'unittest', }) as s:
            _ = 1 + 1
