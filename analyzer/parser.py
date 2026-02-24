"""応答解析モジュール：Tool Call応答のJSON解析と検証。

SAPAICoreClientのconverse_with_toolsが返すTool Call応答を解析し、
InterfaceRecordデータクラスのリストに変換する。
必須フィールドが欠落している場合は警告をログに記録し、
欠落フィールドには空文字列をデフォルト値として使用する。

Validates: Requirements 3.3, 3.5
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger('analyzer')


@dataclass
class InterfaceRecord:
    """Interface設計書から抽出された1行分のレコード。

    出力テンプレート（②_INPUT_EBS定義書の抽出結果.xlsx）のカラム構造に対応:
        文書管理番号 | IF名 | EBSテーブル名 | EBSテーブルID | 項目ID | 項目名 | 桁数
    """

    document_number: str
    if_name: str
    ebs_table_name: str
    ebs_table_id: str
    item_id: str
    item_name: str
    digit_count: str


# 必須フィールド（欠落時に警告を出力するフィールド）
_REQUIRED_FIELDS = ['document_number', 'if_name']


def parse_response(tool_result: dict, file_name: str ,sheet_name: str = None) -> list[InterfaceRecord]:
    """AI応答を解析し、InterfaceRecordリストを返す。

    SAPAICoreClient.converse_with_tools()が返す辞書を解析する。
    期待される入力形式:
        {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'document_number': '...',
                        'if_name': '...',
                        'ebs_table_name': '...',
                        'ebs_table_id': '...',
                        'item_id': '...',
                        'item_name': '...',
                        'digit_count': '...',
                    },
                    ...
                ]
            }
        }

    Args:
        tool_result: converse_with_toolsの戻り値（Tool Call応答辞書）
        file_name: 処理中のファイル名（ログ出力用）

    Returns:
        InterfaceRecordのリスト。応答にinterfacesが含まれない場合は空リスト。
        必須フィールドが欠落している場合でも部分的な結果を含む。

    Validates: Requirements 3.3, 3.5
    """
    records: list[InterfaceRecord] = []
    raw = tool_result.get('extract_interface_info', {})
    interfaces = raw.get('interfaces', [])

    for item in interfaces:
        # 必須フィールドの欠落チェック
        missing = [f for f in _REQUIRED_FIELDS if not item.get(f)]
        if missing:
            logger.warning(
                "File %s: 缺少必填字段 %s", file_name, missing,
            )

        records.append(InterfaceRecord(
            document_number=item.get('document_number', ''),
            if_name=item.get('if_name', ''),
            ebs_table_name=item.get('ebs_table_name', ''),
            ebs_table_id=item.get('ebs_table_id', ''),
            item_id=item.get('item_id', ''),
            item_name=item.get('item_name', ''),
            digit_count=item.get('digit_count', ''),
        ))

    return records
