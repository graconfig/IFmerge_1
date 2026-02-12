"""AI分析モジュール：プロンプト構築、ツール定義、AI呼び出しロジック。

SAPAICoreClientに送信するプロンプトの構築と、
Tool Callingで使用するツール定義（出力テンプレートのカラム構造に一致するスキーマ）を提供する。
また、指数バックオフリトライ付きのAI呼び出しロジックを含む。
"""

import logging
import time

from analyzer.sap_client import SAPAICoreClient

logger = logging.getLogger('analyzer')


def build_analysis_prompt(cleaned_text: str, file_name: str) -> str:
    """構築分析プロンプト。

    クリーニング済みデータとファイル名を含むプロンプトを構築し、
    AIモデルに構造化された情報抽出を依頼する。

    Args:
        cleaned_text: クリーニング済みのテキストデータ（format_as_textの出力）
        file_name: 処理中のInterface設計書のファイル名

    Returns:
        AIモデルに送信するプロンプト文字列

    Validates: Requirements 3.1
    """
    return f"""以下はSAP Interface設計書（{file_name}）の内容です。
この設計書からEBSテーブルの項目情報を抽出してください。

設計書の内容：
{cleaned_text}

上記の内容から、以下の情報を抽出してください：
1. 文書管理番号（document_number）: 設計書の文書管理番号（例: BDN-EPD-OF-093）
2. IF名（if_name）: インターフェース名称
3. EBSテーブル名（ebs_table_name）: EBSテーブルの日本語名称
4. EBSテーブルID（ebs_table_id）: EBSテーブルの英語ID
5. 項目ID（item_id）: 各項目の英語ID/カラム名
6. 項目名（item_name）: 各項目の日本語名称
7. 桁数（digit_count）: 各項目の桁数

重要なルール：
- 「エクスポート項目」等のシートにある項目ID（英語カラム名）を1つずつ漏れなく抽出すること。
- 出力レコード数は、設計書中の項目ID（英語カラム名）の数と完全に一致させること。項目を省略・統合しないこと。
- 各項目IDに対して必ず1行のレコードを出力すること。
- 項目名が項目IDの次の行にある場合は、その日本語名称を対応する項目名として使用すること。

extract_interface_infoツールを使って結果を返してください。"""


def build_tool_definition() -> list[dict]:
    """構築Tool Callingのツール定義。

    出力テンプレート（②_INPUT_EBS定義書の抽出結果.xlsx）のカラム構造に
    一致するスキーマを持つツール定義を返す。

    テンプレートのカラム構造:
        No. | 文書管理番号 | IF名 | EBSテーブル名 | EBSテーブルID | 項目ID | 項目名 | 桁数

    No.は連番のため自動生成し、それ以外の7カラムをスキーマに含める。

    Returns:
        SAP AI Core Converse APIのtoolConfig用ツール定義リスト

    Validates: Requirements 3.2
    """
    return [{
        'toolSpec': {
            'name': 'extract_interface_info',
            'description': '从Interface设计书中提取结构化信息，每个EBSテーブルの各項目を1行として抽出する',
            'inputSchema': {
                'json': {
                    'type': 'object',
                    'properties': {
                        'interfaces': {
                            'type': 'array',
                            'description': '抽出されたインターフェース項目のリスト（各項目が1行に対応）',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'document_number': {
                                        'type': 'string',
                                        'description': '文書管理番号（例: BDN-EPD-OF-093）',
                                    },
                                    'if_name': {
                                        'type': 'string',
                                        'description': 'IF名 - Interface名称',
                                    },
                                    'ebs_table_name': {
                                        'type': 'string',
                                        'description': 'EBSテーブル名 - EBSテーブルの日本語名称',
                                    },
                                    'ebs_table_id': {
                                        'type': 'string',
                                        'description': 'EBSテーブルID - EBSテーブルの英語ID',
                                    },
                                    'item_id': {
                                        'type': 'string',
                                        'description': '項目ID - 各項目の英語ID',
                                    },
                                    'item_name': {
                                        'type': 'string',
                                        'description': '項目名 - 各項目の日本語名称',
                                    },
                                    'digit_count': {
                                        'type': 'string',
                                        'description': '桁数 - 各項目の桁数',
                                    },
                                },
                                'required': [
                                    'document_number',
                                    'if_name',
                                ],
                            },
                        },
                    },
                    'required': ['interfaces'],
                },
            },
        },
    }]

def analyze_with_retry(client: SAPAICoreClient, prompt: str, tools: list,
                       max_retries: int = 3) -> dict | None:
    """AIモデルを呼び出し、失敗時に指数バックオフでリトライする。

    SAPAICoreClientのconverse_with_toolsメソッドを呼び出し、
    API呼び出しが失敗した場合は指数バックオフ（1秒、2秒、4秒）で
    最大max_retries回までリトライする。全リトライ失敗後は例外を再送出する。

    Args:
        client: SAPAICoreClientインスタンス
        prompt: AIモデルに送信するプロンプト文字列
        tools: Tool Callingのツール定義リスト
        max_retries: 最大リトライ回数（デフォルト: 3）

    Returns:
        Tool Call応答の辞書（{tool_name: tool_input}）、
        またはNone（理論上到達しない）

    Raises:
        Exception: 全リトライが失敗した場合、最後の例外を再送出

    Validates: Requirements 3.4, 5.3
    """
    for attempt in range(max_retries):
        try:
            logger.info("AI呼び出し試行 %d/%d", attempt + 1, max_retries)
            result = client.converse_with_tools(prompt, tools, temperature=0.3, max_tokens=16384)
            logger.info("AI呼び出し成功（試行 %d/%d）", attempt + 1, max_retries)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    "AI呼び出し失敗（試行 %d/%d）: %s — %d秒後にリトライします",
                    attempt + 1, max_retries, e, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "AI呼び出し全リトライ失敗（試行 %d/%d）: %s",
                    attempt + 1, max_retries, e,
                )
                raise
    return None
