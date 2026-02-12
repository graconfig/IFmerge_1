import logging
from dataclasses import dataclass

from analyzer.reader import CellData, SheetData

logger = logging.getLogger('analyzer')


@dataclass
class CleanedSheet:
    """清洗後のワークシートデータ。ヘッダー行とデータ行を分離して保持する。"""
    name: str
    headers: list[str]
    rows: list[list[str]]


def clean_sheet_data(sheet: SheetData) -> CleanedSheet | None:
    """清洗单个sheet的数据，返回None表示sheet为空。

    处理规则：
    - 删除线文本的单元格值置为空字符串 (Req 2.2)
    - 非删除线单元格保留原始文本内容，去除首尾空白 (Req 2.3)
    - 移除所有单元格均为空或仅含空白的行 (Req 2.1)
    - 如果清洗后无数据行，返回None并记录日志 (Req 2.5)

    Args:
        sheet: 原始工作表数据

    Returns:
        清洗后的CleanedSheet，如果sheet为空则返回None
    """
    cleaned_rows = []
    for row in sheet.rows:
        cleaned_cells = []
        for cell in row:
            if cell.is_strikethrough:
                cleaned_cells.append("")  # 删除线文本置空
            else:
                cleaned_cells.append(cell.value.strip() if cell.value else "")
        # 跳过全空行
        if any(c for c in cleaned_cells):
            cleaned_rows.append(cleaned_cells)

    if not cleaned_rows:
        logger.info("Sheet '%s' は清洗後に空になったためスキップします", sheet.name)
        return None

    return CleanedSheet(
        name=sheet.name,
        headers=cleaned_rows[0] if cleaned_rows else [],
        rows=cleaned_rows[1:] if len(cleaned_rows) > 1 else [],
    )


def format_as_text(cleaned_sheets: list[CleanedSheet]) -> str:
    """将清洗后的数据格式化为文本，用于AI提示词。

    输出格式：
    - 每个sheet以 "=== Sheet: {name} ===" 开头
    - 只保留非空的单元格值，用 " | " 分隔
    - 第一行为表头
    - 表头下方有分隔线

    Args:
        cleaned_sheets: 清洗后的工作表列表

    Returns:
        格式化后的文本字符串 (Req 2.4)
    """
    parts = []
    for sheet in cleaned_sheets:
        parts.append(f"=== Sheet: {sheet.name} ===")
        all_rows = [sheet.headers] + sheet.rows if sheet.headers else sheet.rows
        if not all_rows:
            continue

        for row_idx, row in enumerate(all_rows):
            # 只保留非空的单元格
            non_empty = [c for c in row if c]
            if non_empty:
                parts.append(" | ".join(non_empty))
            if row_idx == 0 and sheet.headers:
                parts.append("-" * 40)

    return "\n".join(parts)
