"""AI分析モジュール：プロンプト構築、ツール定義、AI呼び出しロジック。

二段階AI呼び出し:
  Phase 1: 全シートの先頭部分を一括送信し、固定情報（文書管理番号、IF名）と
           データ項目を含むシート名を識別
  Phase 2: データ項目シートの行データを分割して項目を抽出
"""

import logging
import time

from analyzer.sap_client import SAPAICoreClient

logger = logging.getLogger('analyzer')

# デフォルト値（AppConfig から上書き可能）
_DEFAULT_PHASE1_HEAD_ROWS = 30
_DEFAULT_MAX_CHUNK_ROWS = 100


def build_phase1_prompt(sheet_head_text: str, file_name: str) -> str:
    """Phase 1: 全シートの先頭部分から固定情報とデータシートを識別する。"""
    return f"""以下はSAP Interface設計書（{file_name}）の各シートの先頭部分です。

{sheet_head_text}

以下を識別してください：
1. document_number: 文書管理番号（例: BDN-EPD-OF-093）
2. if_name: インターフェース名称
3. data_sheets: 項目ID・項目名などのデータ行を含むシート名のリスト
   （「エクスポート項目」「インポート項目」「データ項目」等、
    EBSテーブルの項目一覧が記載されているシートのみ。
    「表紙」「処理概要」「変更履歴」等は除外すること）
4. 各データシートについて、データ行（項目一覧）が始まる行番号（0始まり）

extract_doc_metaツールを使って結果を返してください。"""


def build_phase1_tool() -> list[dict]:
    """Phase 1 用ツール定義。"""
    return [{
        'toolSpec': {
            'name': 'extract_doc_meta',
            'description': '設計書の固定情報とデータシートを識別する',
            'inputSchema': {
                'json': {
                    'type': 'object',
                    'properties': {
                        'document_number': {
                            'type': 'string',
                            'description': '文書管理番号',
                        },
                        'if_name': {
                            'type': 'string',
                            'description': 'IF名',
                        },
                        'data_sheets': {
                            'type': 'array',
                            'description': 'データ項目を含むシートのリスト',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'sheet_name': {
                                        'type': 'string',
                                        'description': 'シート名',
                                    },
                                    'data_start_row': {
                                        'type': 'integer',
                                        'description': 'データ行開始行番号（0始まり）',
                                    },
                                },
                                'required': ['sheet_name', 'data_start_row'],
                            },
                        },
                    },
                    'required': ['document_number', 'if_name', 'data_sheets'],
                },
            },
        },
    }]


def build_phase2_prompt(doc_number: str, if_name: str,
                        chunk_text: str, file_name: str) -> str:
    """Phase 2: 固定情報をコンテキストとして、データ行チャンクから項目を抽出する。"""
    return f"""以下はSAP Interface設計書（{file_name}）のデータ行の一部です。

固定情報（全行共通）：
- 文書管理番号: {doc_number}
- IF名: {if_name}

データ行：
{chunk_text}

上記のデータ行から、各項目を抽出してください。抽出できない情報は空でよい：
1. ebs_table_name: EBSテーブルの日本語名称
2. ebs_table_id: EBSテーブルの英語ID
3. item_id: 各項目の英語ID/カラム名
4. item_name: 各項目の日本語名称
5. digit_count: 各項目の桁数

重要なルール：
- 一セルに複行項目を記載する場合があります。それぞれ分割して出力してください。
- 項目ID（英語カラム名）を1つずつ漏れなく抽出すること。
- 同じNo（番号）に複数の項目IDが属している場合（No列が空白で続く行）は、1行にまとめること：
  * 項目ID: カンマ区切りで連結
  * 項目名: カンマ区切りで連結
  * 桁数: カンマ区切りで連結
- EBSテーブル名/IDはデータ行から読み取ること。途中で変わる場合は変わった後の値を使用。
- 項目名はEBSの項目名のため、注意してください。IF項目のみを出力、処理概要は出力しない。
- 文書管理番号とIF名は上記の固定情報をそのまま使用すること。

extract_interface_infoツールを使って結果を返してください。"""


def build_tool_definition() -> list[dict]:
    """Phase 2 用ツール定義（項目抽出）。"""
    return [{
        'toolSpec': {
            'name': 'extract_interface_info',
            'description': 'EBSテーブルの各項目を抽出する',
            'inputSchema': {
                'json': {
                    'type': 'object',
                    'properties': {
                        'interfaces': {
                            'type': 'array',
                            'description': '抽出された項目リスト',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'document_number': {
                                        'type': 'string',
                                        'description': '文書管理番号',
                                    },
                                    'if_name': {
                                        'type': 'string',
                                        'description': 'IF名',
                                    },
                                    'ebs_table_name': {
                                        'type': 'string',
                                        'description': 'EBSテーブル名',
                                    },
                                    'ebs_table_id': {
                                        'type': 'string',
                                        'description': 'EBSテーブルID',
                                    },
                                    'item_id': {
                                        'type': 'string',
                                        'description': '項目ID',
                                    },
                                    'item_name': {
                                        'type': 'string',
                                        'description': '項目名',
                                    },
                                    'digit_count': {
                                        'type': 'string',
                                        'description': '桁数',
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


def analyze_with_retry(client: SAPAICoreClient, prompt: str,
                       tools: list, max_retries: int = 3) -> dict | None:
    """AI呼び出し（指数バックオフリトライ付き）。"""
    for attempt in range(max_retries):
        try:
            logger.info("AI呼び出し試行 %d/%d", attempt + 1, max_retries)
            result = client.converse_with_tools(
                prompt, tools, temperature=0.3, max_tokens=16384,
            )
            logger.info("AI呼び出し成功（試行 %d/%d）",
                        attempt + 1, max_retries)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    "AI呼び出し失敗（試行 %d/%d）: %s — %d秒後リトライ",
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


def _format_sheet_head(cleaned_sheets: list,
                       max_rows: int = _DEFAULT_PHASE1_HEAD_ROWS) -> str:
    """各シートの先頭N行をフォーマットする。"""
    parts = []
    for sheet in cleaned_sheets:
        parts.append(f"=== Sheet: {sheet.name} ===")
        all_rows = ([sheet.headers] + sheet.rows
                    if sheet.headers else sheet.rows)
        for row_idx, row in enumerate(all_rows[:max_rows]):
            non_empty = [c for c in row if c]
            if non_empty:
                parts.append(f"[Row {row_idx}] " + " | ".join(non_empty))
    return "\n".join(parts)


def _format_data_rows(rows: list[list[str]]) -> str:
    """データ行リストをテキストにフォーマットする。"""
    parts = []
    for row in rows:
        non_empty = [c for c in row if c]
        if non_empty:
            parts.append(" | ".join(non_empty))
    return "\n".join(parts)


def _split_rows_by_count(rows: list[list[str]],
                         max_rows: int = _DEFAULT_MAX_CHUNK_ROWS
                         ) -> list[list[list[str]]]:
    """データ行を固定行数でチャンクに分割する。"""
    if len(rows) <= max_rows:
        return [rows]
    chunks = []
    for i in range(0, len(rows), max_rows):
        chunks.append(rows[i:i + max_rows])
    return chunks


def analyze_file(client: SAPAICoreClient, cleaned_sheets: list,
                 file_name: str,
                 phase1_head_rows: int = _DEFAULT_PHASE1_HEAD_ROWS,
                 max_chunk_rows: int = _DEFAULT_MAX_CHUNK_ROWS,
                 ) -> list[dict]:
    """二段階AI呼び出しでファイルを分析する。

    Phase 1: 全シートの先頭部分を一括送信し、
             固定情報（文書管理番号、IF名）とデータシートを識別
    Phase 2: データシートの行データを分割して項目を抽出

    Args:
        client: SAPAICoreClient インスタンス
        cleaned_sheets: CleanedSheet のリスト
        file_name: ファイル名
        phase1_head_rows: Phase 1 で送信するシート先頭の最大行数
        max_chunk_rows: Phase 2 の1チャンクあたりの最大行数

    Returns:
        全チャンクの tool_result リスト
    """
    # --- Phase 1: 固定情報 + データシート識別 ---
    logger.info("Phase 1: 固定情報とデータシートを識別します。")
    head_text = _format_sheet_head(cleaned_sheets, max_rows=phase1_head_rows)
    phase1_prompt = build_phase1_prompt(head_text, file_name)
    phase1_tools = build_phase1_tool()
    phase1_result = analyze_with_retry(
        client, phase1_prompt, phase1_tools,
    )

    if not phase1_result:
        logger.error("Phase 1 失敗。")
        return []

    meta = phase1_result.get('extract_doc_meta', {})
    doc_number = meta.get('document_number', '')
    if_name = meta.get('if_name', '')
    data_sheets_meta = meta.get('data_sheets', [])

    logger.info(
        "Phase 1 完了: doc=%s, if=%s, データシート=%d件",
        doc_number, if_name, len(data_sheets_meta),
    )

    # データシート名のセット
    ds_map = {
        ds['sheet_name']: ds.get('data_start_row', 0)
        for ds in data_sheets_meta
    }

    # --- Phase 2: データシートごとに行データを分割して抽出 ---
    all_results = []
    tools = build_tool_definition()

    for sheet in cleaned_sheets:
        if sheet.name not in ds_map:
            logger.info("Sheet '%s' はデータシートでないためスキップ。",
                        sheet.name)
            continue

        data_start = ds_map[sheet.name]
        all_rows = ([sheet.headers] + sheet.rows
                    if sheet.headers else sheet.rows)
        data_rows = all_rows[data_start:]

        if not data_rows:
            logger.info("Sheet '%s' のデータ行が空。", sheet.name)
            continue

        chunks = _split_rows_by_count(data_rows, max_rows=max_chunk_rows)
        logger.info(
            "Phase 2: Sheet '%s' — %d行を%dチャンクで処理。",
            sheet.name, len(data_rows), len(chunks),
        )

        for ci, chunk in enumerate(chunks, 1):
            chunk_text = _format_data_rows(chunk)
            prompt = build_phase2_prompt(
                doc_number, if_name, chunk_text, file_name,
            )
            logger.info(
                "Phase 2: Sheet '%s' チャンク %d/%d",
                sheet.name, ci, len(chunks),
            )
            result = analyze_with_retry(client, prompt, tools)
            if result:
                all_results.append(result)

    return all_results
