from pathlib import Path


def scan_excel_files(input_dir: str) -> list[Path]:
    """返回input_dir下所有.xlsx和.xls文件的路径列表，按文件名排序。

    扫描指定目录，识别所有Excel文件（.xlsx和.xls扩展名），
    排除以~$开头的临时文件，结果按文件名排序返回。

    Args:
        input_dir: 要扫描的目录路径

    Returns:
        按文件名排序的Excel文件Path列表
    """
    patterns = ['*.xlsx', '*.xls', '*.xlsm']
    files = []
    for pattern in patterns:
        files.extend(Path(input_dir).glob(pattern))
    # 排除以~$开头的临时文件
    files = [f for f in files if not f.name.startswith('~$')]
    return sorted(files, key=lambda f: f.name)
