"""运行时路径解析:兼容开发态与 PyInstaller 打包态。

放在 analyzer(底层包)中,使 analyzer 与 analyzer_gui 都能引用而不产生
反向依赖(analyzer_gui -> analyzer 是允许方向)。

两类路径:
  - resource_path():只读资源(prompts.yaml / reference 模板 / locales)。
        打包后位于 sys._MEIPASS(PyInstaller 解压目录);开发态= 仓库根。
  - app_data_dir():可写数据(.env / input / output / 日志)。
        打包后= 可执行文件同级目录(用户可见、可持久化);开发态= 仓库根。
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """是否运行于 PyInstaller 打包后的可执行文件中。"""
    return bool(getattr(sys, "frozen", False))


def _repo_root() -> Path:
    # runtime.py 位于 <root>/analyzer/runtime.py,parents[1] = <root>。
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    """只读资源根目录下的路径。

    打包后基准= sys._MEIPASS;开发态= 仓库根。
    """
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", _repo_root()))
    else:
        base = _repo_root()
    return base.joinpath(*parts)


def app_data_dir() -> Path:
    """可写数据根目录(.env / input / output / 日志 所在)。

    打包后= 可执行文件所在目录(onefile 时为真实 exe 位置,而非临时解压目录);
    开发态= 仓库根。
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return _repo_root()
