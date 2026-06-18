"""日志器封装。控制台 + 文件双输出。"""

import logging
import sys
from pathlib import Path


def setup_logger(level: str = "INFO", log_file: str = "output/analyzer_gui.log"):
    """初始化全局 logger（root = 'analyzer_gui'），重复调用安全。"""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    root = logging.getLogger("analyzer_gui")
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    root.addHandler(sh)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    root.addHandler(fh)

    return root
