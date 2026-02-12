"""日志管理器 - 统一管理控制台和文件日志输出。

Provides setup_logger() to configure a logger that writes to both
the console (stdout) and a log file in the specified output directory.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import logging
import os


def setup_logger(output_dir: str) -> logging.Logger:
    """配置日志器，同时输出到控制台和文件。

    Creates the output directory if it does not exist, then returns a
    logger named 'analyzer' with two handlers:
      - A StreamHandler for console output (stdout)
      - A FileHandler writing to ``<output_dir>/analyzer.log`` (UTF-8)

    Both handlers use the format ``%(asctime)s [%(levelname)s] %(message)s``.

    If the logger already has handlers (e.g. from a previous call), the
    existing handlers are cleared first to avoid duplicate log lines.

    Args:
        output_dir: Path to the directory where the log file will be written.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    os.makedirs(output_dir, exist_ok=True)

    logger = logging.getLogger("analyzer")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers when setup_logger is called multiple times
    if logger.handlers:
        logger.handlers.clear()

    log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # 文件handler
    log_path = os.path.join(output_dir, "analyzer.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger
