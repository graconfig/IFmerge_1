#!/usr/bin/env python3
"""Excel Interface設計書分析ツール — メインエントリポイント。

全モジュールを連携させて以下のパイプラインを実行する:
  配置加载 → 文件扫描 → 循环处理（読取→清洗→AI分析→解析）→ 出力Excel → 日志摘要

単一ファイルの処理失敗は全体フローに影響しない（Req 1.4, 3.4）。
"""

import sys
from pathlib import Path

from analyzer.ai_analyzer import analyze_file
from analyzer.cleaner import clean_sheet_data
from analyzer.config import load_config
from analyzer.formatter import write_new_format
from analyzer.logger import setup_logger
from analyzer.parser import parse_response
from analyzer.reader import read_excel
from analyzer.sap_client import SAPAICoreClient
from analyzer.scanner import scan_excel_files
from analyzer.writer import write_output_excel


def main() -> None:
    """メイン処理フロー。"""

    # ------------------------------------------------------------------
    # 1. 配置加载 — 必要な環境変数が欠落している場合は exit code 1（Req 5.2）
    # ------------------------------------------------------------------
    try:
        config = load_config()
    except ValueError as exc:
        print(f"[ERROR] 設定エラー: {exc}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. ロガーセットアップ（Req 6.4）
    # ------------------------------------------------------------------
    logger = setup_logger(config.output_dir)

    # ------------------------------------------------------------------
    # 3. input ディレクトリをスキャンして Excel ファイルを取得（Req 1.1）
    # ------------------------------------------------------------------
    files = scan_excel_files(config.input_dir)

    # Req 1.3: ファイルが見つからない場合はメッセージを出力して正常終了
    if not files:
        logger.info(
            "input ディレクトリ '%s' に Excel ファイルが見つかりませんでした。処理を終了します。",
            config.input_dir,
        )
        sys.exit(0)

    # Req 6.1: 処理開始時にファイル総数をログ出力
    total_files = len(files)
    logger.info("Excel ファイルを %d 件検出しました。処理を開始します。", total_files)

    # ------------------------------------------------------------------
    # 4. SAPAICoreClient インスタンスを準備
    # ------------------------------------------------------------------
    client = SAPAICoreClient(config)

    # ------------------------------------------------------------------
    # 5. ファイルごとの処理ループ（Req 1.2: 逐個順次処理）
    # ------------------------------------------------------------------
    all_records = []
    success_count = 0
    failure_count = 0

    for idx, file_path in enumerate(files, 1):
        file_name = file_path.name

        # Req 6.2: 現在のファイル名と位置をログ出力
        logger.info("Processing file %d/%d: %s", idx, total_files, file_name)

        try:
            # 5a. Excel 読取（Req 1.5）
            sheets = read_excel(file_path)

            # 5b. データ清洗（Req 2.1–2.5）
            cleaned_sheets = []
            for sheet in sheets:
                cleaned = clean_sheet_data(sheet)
                if cleaned is not None:
                    cleaned_sheets.append(cleaned)

            if not cleaned_sheets:
                logger.warning(
                    "File %s: 全シートが清洗後に空のためスキップします。", file_name,
                )
                failure_count += 1
                continue

            # 5c. 二段階AI分析（Phase1: 固定情報識別, Phase2: 項目抽出）
            tool_results = analyze_file(
                client, cleaned_sheets, file_name,
                phase1_head_rows=config.phase1_head_rows,
                max_chunk_rows=config.max_chunk_rows,
            )

            # 5d. 応答解析（Req 3.3, 3.5）
            records = []
            for tool_result in tool_results:
                records.extend(parse_response(tool_result, file_name))
            all_records.extend(records)

            logger.info(
                "File %s: %d 件のレコードを抽出しました。", file_name, len(records),
            )

            # 5e. 新フォーマット出力（ファイルごとに1つ生成）
            if records:
                if_name_for_file = records[0].if_name if hasattr(records[0], 'if_name') else records[0].get('if_name', '')
                try:
                    write_new_format(
                        records=records,
                        if_name=if_name_for_file,
                        input_filename=file_name,
                        template_path=Path(config.template_path),
                        reference_path=Path(config.reference_path),
                        output_dir=Path(config.output_dir),
                    )
                except Exception as fmt_exc:
                    logger.warning(
                        "File %s: 新フォーマット出力に失敗しました: %s", file_name, fmt_exc,
                    )

            success_count += 1

        except Exception as exc:
            # Req 1.4, 3.4: 単一ファイルの失敗はログに記録してスキップ
            logger.error(
                "File %s の処理中にエラーが発生しました: %s", file_name, exc,
            )
            failure_count += 1
            continue

    # ------------------------------------------------------------------
    # 6. 結果を Excel に出力（Req 4.1–4.5）
    # ------------------------------------------------------------------
    if all_records:
        output_path = write_output_excel(all_records, config.output_dir)
    else:
        output_path = "(レコードなし — 出力ファイルは生成されませんでした)"
        logger.warning("抽出レコードが 0 件のため、出力ファイルは生成されませんでした。")

    # ------------------------------------------------------------------
    # 7. 処理サマリーをログ出力（Req 6.3）
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("処理完了サマリー")
    logger.info("  対象ファイル数: %d", total_files)
    logger.info("  成功: %d", success_count)
    logger.info("  失敗: %d", failure_count)
    logger.info("  抽出レコード数: %d", len(all_records))
    logger.info("  出力ファイル: %s", output_path)
    logger.info("=" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()
