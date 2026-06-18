"""文件系统工具:递归扫描 Excel、跨平台打开文件夹。"""

import os
import subprocess
import sys
from pathlib import Path

EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}  # 与 analyzer.reader 支持的格式一致


def find_excel_files(folder: Path) -> list[Path]:
    """递归扫描文件夹下所有 .xlsx,跳过 Excel 临时锁文件(~$ 前缀)。"""
    folder = Path(folder)
    result = []
    for p in sorted(folder.rglob("*")):
        if (p.is_file()
                and p.suffix.lower() in EXCEL_SUFFIXES
                and not p.name.startswith("~$")):
            result.append(p)
    return result


def open_folder(folder: Path) -> None:
    """用系统资源管理器打开文件夹(跨平台);目录不存在则创建。"""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(folder))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(folder)], check=False)
    else:
        subprocess.run(["xdg-open", str(folder)], check=False)
