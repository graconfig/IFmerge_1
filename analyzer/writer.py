"""Excel出力モジュール：分析結果をExcelファイルに書き出す。

全InterfaceRecordをOutput_Template（②_INPUT_EBS定義書の抽出結果.xlsx）の
カラム構造に従ってExcelファイルに書き出す。
出力ディレクトリが存在しない場合は自動作成し、
ファイル名にはタイムスタンプを付与して上書きを防止する。

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

import os
from datetime import datetime

from openpyxl import Workbook

from analyzer.parser import InterfaceRecord


def write_output_excel(records: list[InterfaceRecord], output_dir: str) -> str:
    """分析結果をExcelファイルに書き出し、出力ファイルパスを返す。

    Output_Template（②_INPUT_EBS定義書の抽出結果.xlsx）のカラム構造に従い、
    各InterfaceRecordを1行として書き出す。先頭列にはNo.（連番）を付与する。

    Args:
        records: 書き出すInterfaceRecordのリスト。
        output_dir: 出力先ディレクトリパス。存在しない場合は自動作成される。

    Returns:
        生成されたExcelファイルの絶対パスまたは相対パス。

    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
    """
    # Req 4.4: output/extracted/ディレクトリが存在しない場合は自動作成
    extracted_dir = os.path.join(output_dir, 'extracted')
    os.makedirs(extracted_dir, exist_ok=True)

    # Req 4.5: タイムスタンプパターンでファイル名を生成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"EBS定義書_抽出結果_{timestamp}.xlsx"
    filepath = os.path.join(extracted_dir, filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "抽出結果"

    # Req 4.2: Output_Templateのカラム構造に従ったヘッダー行
    headers = [
        'No.', '文書管理番号', 'IF名', 'EBSテーブル名',
        'EBSテーブルID', '項目ID', '項目名', '桁数',
    ]
    ws.append(headers)

    # Req 4.3: 各InterfaceRecordを1行として書き出す（空白セルは"-"で埋める）
    for i, record in enumerate(records, 1):
        ws.append([
            i,
            record.document_number or '-',
            record.if_name or '-',
            record.ebs_table_name or '-',
            record.ebs_table_id or '-',
            record.item_id or '-',
            record.item_name or '-',
            record.digit_count or '-',
        ])

    wb.save(filepath)
    return filepath
