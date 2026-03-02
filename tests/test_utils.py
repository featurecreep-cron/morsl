from __future__ import annotations

from datetime import datetime

import pytest

from utils import format_date, setup_logging, split_offset, string_to_date


class TestStringToDate:
    def test_valid_date(self):
        date, after = string_to_date("2024-01-15")
        assert isinstance(date, datetime)
        assert date.year == 2024
        assert date.month == 1
        assert date.day == 15
        assert after is True

    def test_negative_date(self):
        date, after = string_to_date("-2024-01-15")
        assert isinstance(date, datetime)
        assert after is False

    def test_invalid_format(self):
        date, after = string_to_date("not-a-date")
        assert date is False
        assert after is False

    def test_invalid_month(self):
        date, _after = string_to_date("2024-13-01")
        assert date is False


class TestSplitOffset:
    def test_days_format(self):
        after, offset, interval = split_offset("7days")
        assert after is True
        assert offset == 7
        assert interval == "days"

    def test_negative_offset(self):
        after, offset, _interval = split_offset("-14days")
        assert after is False
        assert offset == 14

    def test_number_only(self):
        after, offset, interval = split_offset("30")
        assert after is True
        assert offset == 30
        assert interval == ""

    def test_case_insensitive(self):
        _after, offset, interval = split_offset("7Days")
        assert offset == 7
        assert interval == "days"

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid time offset"):
            split_offset("abc")


class TestFormatDate:
    def test_absolute_date(self):
        date, after = format_date("2024-06-15")
        assert date.year == 2024
        assert date.month == 6
        assert date.day == 15
        assert after is True

    def test_relative_offset(self):
        date, after = format_date("7days")
        assert isinstance(date, datetime)
        # relative date should be approximately 7 days in the past
        assert after is True

    def test_future_offset(self):
        date, _after = format_date("7days", future=True)
        assert isinstance(date, datetime)
        assert date > datetime.now(date.tzinfo)


class TestSetupLogging:
    def setup_method(self):
        """Remove the CreateMenu logger handlers before each test."""
        import logging

        logger = logging.getLogger("morsl")
        logger.handlers.clear()
        if hasattr(logger, "loglevel"):
            del logger.loglevel

    def test_subsequent_call_updates_stdout_level(self):
        import logging
        import sys

        logger = setup_logging("INFO")
        assert logger.loglevel == logging.INFO
        handler_count = len(logger.handlers)
        # Find stdout handler level
        stdout_h = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout]
        assert len(stdout_h) == 1
        assert stdout_h[0].level == logging.INFO

        # Second call with different level
        logger2 = setup_logging("DEBUG")
        assert logger2 is logger
        assert logger2.loglevel == logging.DEBUG
        # Handler count unchanged
        assert len(logger2.handlers) == handler_count
        stdout_h2 = [h for h in logger2.handlers if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout]
        assert stdout_h2[0].level == logging.DEBUG

    def test_log_to_stdout_skips_file_handler(self):
        import logging

        logger = setup_logging("INFO", log_to_stdout=True)
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_subsequent_call_leaves_stderr_handler_unchanged(self):
        import logging
        import sys

        logger = setup_logging("INFO")
        stderr_h = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and h.stream is sys.stderr]
        assert len(stderr_h) == 1
        original_level = stderr_h[0].level

        setup_logging("DEBUG")
        assert stderr_h[0].level == original_level
