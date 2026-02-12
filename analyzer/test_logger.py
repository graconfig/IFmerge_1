"""Tests for the logger module (Requirements 6.1, 6.2, 6.3, 6.4)."""

import logging
import os

import pytest

from analyzer.logger import setup_logger


@pytest.fixture(autouse=True)
def _clean_logger():
    """Remove all handlers from the 'analyzer' logger before each test."""
    logger = logging.getLogger("analyzer")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_returns_logger_instance(self, tmp_path):
        """setup_logger should return a logging.Logger."""
        logger = setup_logger(str(tmp_path))
        assert isinstance(logger, logging.Logger)

    def test_logger_name_is_analyzer(self, tmp_path):
        """setup_logger should return a logger named 'analyzer'."""
        logger = setup_logger(str(tmp_path))
        assert logger.name == "analyzer"

    def test_logger_level_is_info(self, tmp_path):
        """setup_logger should set the logger level to INFO."""
        logger = setup_logger(str(tmp_path))
        assert logger.level == logging.INFO

    def test_has_two_handlers(self, tmp_path):
        """setup_logger should attach exactly two handlers (console + file)."""
        logger = setup_logger(str(tmp_path))
        assert len(logger.handlers) == 2

    def test_has_stream_handler(self, tmp_path):
        """setup_logger should include a StreamHandler for console output."""
        logger = setup_logger(str(tmp_path))
        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) == 1

    def test_has_file_handler(self, tmp_path):
        """setup_logger should include a FileHandler for file output."""
        logger = setup_logger(str(tmp_path))
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

    def test_log_file_created(self, tmp_path):
        """setup_logger should create analyzer.log in the output directory."""
        setup_logger(str(tmp_path))
        log_file = tmp_path / "analyzer.log"
        assert log_file.exists()

    def test_creates_output_directory(self, tmp_path):
        """setup_logger should create the output directory if it doesn't exist."""
        new_dir = tmp_path / "nested" / "output"
        setup_logger(str(new_dir))
        assert new_dir.is_dir()

    def test_writes_to_log_file(self, tmp_path):
        """Log messages should be written to the log file (Req 6.4)."""
        logger = setup_logger(str(tmp_path))
        logger.info("test message")
        log_file = tmp_path / "analyzer.log"
        content = log_file.read_text(encoding="utf-8")
        assert "test message" in content
        assert "[INFO]" in content

    def test_log_format_contains_timestamp(self, tmp_path):
        """Log messages should include a timestamp."""
        logger = setup_logger(str(tmp_path))
        logger.info("timestamp check")
        log_file = tmp_path / "analyzer.log"
        content = log_file.read_text(encoding="utf-8")
        # Timestamp format: YYYY-MM-DD HH:MM:SS,mmm
        assert "[INFO]" in content
        # Verify there's content before [INFO] (the timestamp)
        line = content.strip().split("\n")[0]
        assert line.index("[INFO]") > 0

    def test_no_duplicate_handlers_on_repeated_calls(self, tmp_path):
        """Calling setup_logger multiple times should not add duplicate handlers."""
        setup_logger(str(tmp_path))
        logger = setup_logger(str(tmp_path))
        assert len(logger.handlers) == 2

    def test_file_handler_uses_utf8(self, tmp_path):
        """The file handler should use UTF-8 encoding for Japanese text support."""
        logger = setup_logger(str(tmp_path))
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert file_handlers[0].encoding == "utf-8"

    def test_writes_japanese_text(self, tmp_path):
        """Logger should correctly write Japanese text to the log file."""
        logger = setup_logger(str(tmp_path))
        logger.info("処理開始: ファイル数 5")
        log_file = tmp_path / "analyzer.log"
        content = log_file.read_text(encoding="utf-8")
        assert "処理開始: ファイル数 5" in content

    def test_writes_to_console(self, tmp_path, capsys):
        """Log messages should be written to console/stdout (Req 6.4)."""
        logger = setup_logger(str(tmp_path))
        logger.info("console output test")
        captured = capsys.readouterr()
        assert "console output test" in captured.err  # StreamHandler defaults to stderr

    def test_log_file_path(self, tmp_path):
        """The log file should be named 'analyzer.log' in the output directory."""
        logger = setup_logger(str(tmp_path))
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        expected_path = os.path.join(str(tmp_path), "analyzer.log")
        assert file_handlers[0].baseFilename == expected_path
