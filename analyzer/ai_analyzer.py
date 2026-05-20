"""AI分析モジュール：プロンプト構築、ツール定義、AI呼び出しロジック。

二段階AI呼び出し:
  Phase 1: 全シートの先頭部分を一括送信し、固定情報（文書管理番号、IF名）と
           データ項目を含むシート名を識別
  Phase 2: データ項目シートの行データを分割して項目を抽出
"""

import logging
import time
from pathlib import Path

from analyzer.sap_client import SAPAICoreClient

logger = logging.getLogger('analyzer')

# デフォルト値（AppConfig から上書き可能）
_DEFAULT_PHASE1_HEAD_ROWS = 30
_DEFAULT_MAX_CHUNK_ROWS = 100

_PROMPTS_FILE = Path('prompts.yaml')
_templates_cache: dict | None = None


def _load_prompt_templates() -> dict:
    """Load prompts.yaml once and cache. Returns {} on any failure."""
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache
    try:
        import yaml
        with open(_PROMPTS_FILE, encoding='utf-8') as f:
            _templates_cache = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning("prompts.yaml が見つかりません。内蔵プロンプトを使用します。")
        _templates_cache = {}
    except Exception as e:
        logger.warning(
            "prompts.yaml の読み込みに失敗しました: %s — 内蔵プロンプトを使用します。", e,
        )
        _templates_cache = {}
    return _templates_cache


def build_phase1_prompt(sheet_head_text: str, file_name: str) -> str:
    """Phase 1: 全シートの先頭部分から固定情報・データシート・列構造を識別する。"""
    tmpl = _load_prompt_templates().get('phase1', {}).get('template')
    if tmpl:
        try:
            return tmpl.format(file_name=file_name, sheet_head_text=sheet_head_text)
        except (KeyError, ValueError) as e:
            logger.warning(
                "phase1テンプレートの展開に失敗しました: %s — 内蔵プロンプトを使用します。", e,
            )
    return f"""以下はSAP Interface設計書（{file_name}）の各シートの先頭部分です。
各行の各セルは [列番号]値 の形式で表示されています。

{sheet_head_text}

以下を識別してください：
1. document_number: 文書管理番号（例: BDN-EPD-OF-093）
2. if_name: インターフェース名称
3. data_sheets: EBSテーブルの項目一覧が記載されているシートのみ
   （「エクスポート項目」「インポート項目」「データ項目」等。
    「表紙」「処理概要」「変更履歴」「テーブル一覧」等は除外すること）
4. 各データシートについて：
   - data_start_row: データ行（項目一覧）が始まる行番号（0始まり）
   - col_table_name: EBSテーブル名（日本語）が入っている列番号（不明な場合は-1）
   - col_table_id: EBSテーブルID（英語）が入っている列番号
   - col_item_id: 項目ID（英語カラム名）が入っている列番号
   - col_digit: 桁数（バイト長）が入っている列番号（不明な場合は-1）

extract_doc_metaツールを使って結果を返してください。"""


def build_phase1_tool() -> list[dict]:
    """Phase 1 用ツール定義。"""
    return [{
        'toolSpec': {
            'name': 'extract_doc_meta',
            'description': '設計書の固定情報・データシート・列構造を識別する',
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
                                    'col_table_name': {
                                        'type': 'integer',
                                        'description': 'EBSテーブル名（日本語）列番号（不明は-1）',
                                    },
                                    'col_table_id': {
                                        'type': 'integer',
                                        'description': 'EBSテーブルID列番号',
                                    },
                                    'col_item_id': {
                                        'type': 'integer',
                                        'description': '項目ID列番号',
                                    },
                                    'col_digit': {
                                        'type': 'integer',
                                        'description': '桁数列番号（不明は-1）',
                                    },
                                },
                                'required': [
                                    'sheet_name', 'data_start_row',
                                    'col_table_id', 'col_item_id',
                                ],
                            },
                        },
                    },
                    'required': ['document_number', 'if_name', 'data_sheets'],
                },
            },
        },
    }]


def build_phase2_prompt(doc_number: str, if_name: str,
                        chunk_text: str, file_name: str,
                        col_table_name: int = -1, col_table_id: int = -1,
                        col_item_id: int = -1, col_digit: int = -1) -> str:
    """Phase 2: 固定情報をコンテキストとして、データ行チャンクから項目を抽出する。"""
    tmpl = _load_prompt_templates().get('phase2', {}).get('template')
    if tmpl:
        try:
            return tmpl.format(
                file_name=file_name, doc_number=doc_number,
                if_name=if_name, chunk_text=chunk_text,
            )
        except (KeyError, ValueError) as e:
            logger.warning(
                "phase2テンプレートの展開に失敗しました: %s — 内蔵プロンプトを使用します。", e,
            )
    return f"""以下はSAP Interface設計書（{file_name}）のデータ行の一部です。
各セルは [列番号]値 の形式で表示されています。

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
6. item_description: 項目の詳細説明（備考欄や説明欄から取得）
7. data_type: データ型（VARCHAR2, NUMBER, DATE等）
8. digit_decimal: 桁数（小数点以下）
9. dev_type: 標準/追加開発
10. is_key: キー項目（●など）
11. required: 必須/任意
12. remarks: 備考

重要なルール：
- 一セルに複数行の項目が記載されている場合は、それぞれ分割して出力すること。
- 項目ID（英語カラム名）を1つずつ漏れなく抽出すること。
- 同じNo（番号）に複数の項目IDが属している場合（No列が空白で続く行）は、1行にまとめること：
  * 項目ID: カンマ区切りで連結
  * 項目名: カンマ区切りで連結
  * 桁数: カンマ区切りで連結
- EBSテーブル名/IDはデータ行から読み取ること。途中で変わる場合は変わった後の値を使用。
- IF項目のみを出力すること。処理概要などの説明行は出力しないこと。
- 文書管理番号とIF名は上記の固定情報をそのまま使用すること。
- セル内のノイズ除去ルール：
  * 【履歴管理】およびそれ以降の文字列（番号・記号・丸数字含む）はすべて除去すること（例: 「契約情報　【履歴管理】④」→「契約情報」）
  * [Vx.xx]形式のバージョン番号は除去すること（例: 「TAX代替ビュー(ID)  [V1.09]」→「TAX代替ビュー(ID)」）
  * セルに「×」「＊」「*」などの演算記号が含まれる場合、その記号より前の英語ID部分のみを使用すること（例: 「TAX_RATE  ×  0.01」→「TAX_RATE」）
  * 項目IDセルの値が演算記号のみ、または演算記号で始まる場合（英語IDが含まれない場合）はその行をスキップすること

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
                                        'description': '項目名（日本語）',
                                    },
                                    'item_description': {
                                        'type': 'string',
                                        'description': '項目説明（項目の詳細説明）',
                                    },
                                    'digit_count': {
                                        'type': 'string',
                                        'description': '桁数',
                                    },
                                    'data_type': {
                                        'type': 'string',
                                        'description': 'データ型（VARCHAR2, NUMBER, DATE等）',
                                    },
                                    'digit_decimal': {
                                        'type': 'string',
                                        'description': '桁数（小数点以下）',
                                    },
                                    'dev_type': {
                                        'type': 'string',
                                        'description': '標準/追加開発',
                                    },
                                    'is_key': {
                                        'type': 'string',
                                        'description': 'キー項目（●など）',
                                    },
                                    'required': {
                                        'type': 'string',
                                        'description': '必須/任意',
                                    },
                                    'remarks': {
                                        'type': 'string',
                                        'description': '備考',
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
    """各シートの先頭N行を [列番号]値 形式でフォーマットする。"""
    parts = []
    for sheet in cleaned_sheets:
        parts.append(f"=== Sheet: {sheet.name} ===")
        all_rows = ([sheet.headers] + sheet.rows
                    if sheet.headers else sheet.rows)
        for row_idx, row in enumerate(all_rows[:max_rows]):
            tagged = ["[%d]%s" % (ci, c) for ci, c in enumerate(row) if c]
            if tagged:
                parts.append("[Row %d] %s" % (row_idx, "  ".join(tagged)))
    return "\n".join(parts)


def _filter_columns(rows: list[list[str]],
                    col_indices: list[int]) -> list[list[str]]:
    """指定された列インデックスのみを残す。col_indicesが空の場合は全列を返す。"""
    if not col_indices:
        return rows
    valid = sorted(set(i for i in col_indices if i >= 0))
    if not valid:
        return rows
    result = []
    for row in rows:
        filtered = [row[i] if i < len(row) else '' for i in valid]
        result.append(filtered)
    return result


def _format_data_rows(rows: list[list[str]],
                      col_offset: list[int] | None = None) -> str:
    """データ行リストを [列番号]値 形式でフォーマットする。

    col_offset: 各列の元の列番号リスト（_filter_columns後の列に対応）
    """
    parts = []
    for row in rows:
        tagged = []
        for ci, cell in enumerate(row):
            if cell:
                orig_col = col_offset[ci] if col_offset and ci < len(col_offset) else ci
                tagged.append("[%d]%s" % (orig_col, cell))
        if tagged:
            parts.append("  ".join(tagged))
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

    # データシート名のセット（data_start_row + 列情報）
    ds_map = {
        ds['sheet_name']: ds
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

        ds_info = ds_map[sheet.name]
        data_start = ds_info.get('data_start_row', 0)
        col_table_name = ds_info.get('col_table_name', -1)
        col_table_id = ds_info.get('col_table_id', -1)
        col_item_id = ds_info.get('col_item_id', -1)
        col_digit = ds_info.get('col_digit', -1)

        # 送信する列を絞り込む（-1 は除外）
        col_indices = [c for c in [col_table_name, col_table_id, col_item_id, col_digit] if c >= 0]
        col_indices_sorted = sorted(set(col_indices))

        all_rows = ([sheet.headers] + sheet.rows
                    if sheet.headers else sheet.rows)
        data_rows = all_rows[data_start:]

        if not data_rows:
            logger.info("Sheet '%s' のデータ行が空。", sheet.name)
            continue

        # 列フィルタリング
        if col_indices_sorted:
            filtered_rows = _filter_columns(data_rows, col_indices_sorted)
            logger.info(
                "Sheet '%s': 列%s に絞り込み（元%d列→%d列）",
                sheet.name, col_indices_sorted,
                len(data_rows[0]) if data_rows else 0,
                len(col_indices_sorted),
            )
        else:
            filtered_rows = data_rows
            col_indices_sorted = None

        chunks = _split_rows_by_count(filtered_rows, max_rows=max_chunk_rows)
        logger.info(
            "Phase 2: Sheet '%s' — %d行を%dチャンクで処理。",
            sheet.name, len(filtered_rows), len(chunks),
        )

        for ci, chunk in enumerate(chunks, 1):
            chunk_text = _format_data_rows(chunk, col_offset=col_indices_sorted)
            prompt = build_phase2_prompt(
                doc_number, if_name, chunk_text, file_name,
                col_table_name=col_table_name,
                col_table_id=col_table_id,
                col_item_id=col_item_id,
                col_digit=col_digit,
            )
            logger.info(
                "Phase 2: Sheet '%s' チャンク %d/%d",
                sheet.name, ci, len(chunks),
            )
            result = analyze_with_retry(client, prompt, tools)
            if result:
                all_results.append(result)

    return all_results
