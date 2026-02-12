#!/usr/bin/env python3
"""Excel Interface設計書分析ツール — メインエントリポイント。

全モジュールを連携させて以下のパイプラインを実行する:
  配置加载 → 文件扫描 → 循环处理（読取→清洗→AI分析→解析）→ 出力Excel → 日志摘要

単一ファイルの処理失敗は全体フローに影響しない（Req 1.4, 3.4）。
"""

import sys

from analyzer.config import load_config
from analyzer.scanner import scan_excel_files
from analyzer.reader import read_excel
from analyzer.cleaner import clean_sheet_data, format_as_text
from analyzer.ai_analyzer import (
    build_analysis_prompt,
    build_tool_definition,
    analyze_with_retry,
)
from analyzer.parser import parse_response
from analyzer.writer import write_output_excel
from analyzer.logger import setup_logger
from analyzer.sap_client import SAPAICoreClient


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
    # 4. SAPAICoreClient インスタンスとツール定義を準備
    # ------------------------------------------------------------------
    client = SAPAICoreClient(config)
    tools = build_tool_definition()

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

            # 5c. テキストフォーマット → プロンプト構築（Req 2.4, 3.1）
            cleaned_text = format_as_text(cleaned_sheets)
            prompt = build_analysis_prompt(cleaned_text, file_name)

            # 5d. AI 分析（Req 3.2, 3.4 — リトライ付き）
            tool_result = analyze_with_retry(client, prompt, tools)

            # 5e. 応答解析（Req 3.3, 3.5）
            records = parse_response(tool_result, file_name)
            all_records.extend(records)

            logger.info(
                "File %s: %d 件のレコードを抽出しました。", file_name, len(records),
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
