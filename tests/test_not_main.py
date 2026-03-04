# File: test_not_main.py
# Date: 2026/3/2
# Desc:

import logging
import unittest

import memlog

logging.basicConfig(level=logging.WARNING, format='%(asctime)s "%(pathname)s:%(lineno)s" - %(message)s')
logger = logging.getLogger(__name__)


class TestMain(unittest.TestCase):
    def setUp(self):
        memlog.start()

    def tearDown(self):
        memlog.stop()

    def test_get_first_snapshot(self):
        assert memlog.get_first_snapshot() is None

    def test_take_snapshot(self):
        # 确保有一些内存分配
        import numpy as np
        _ = np.array([i for i in range(100)])
        assert memlog.take_snapshot(filters=['numpy']) is None

    def test_snapshot(self):
        @memlog.snapshot(top_k=1, title='test', filters=[])
        def test_func():
            return 1 + 1

        _ = test_func()

    def test_snapshot_manager(self):
        with memlog.snapshot_manager(top_k=1, title='test', filters=None) as s:
            _ = 1 + 1
