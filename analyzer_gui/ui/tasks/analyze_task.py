"""解析后台任务(进程内调用 analyzer,编排镜像自 main.py)。

通过给 'analyzer' logger 挂一个 Handler,把原程序的日志原样转发到 GUI 日志框,
从而与原工程的日志完全一致。
"""

import logging
import threading
from pathlib import Path
from typing import Callable, List

from analyzer.ai_analyzer import analyze_file
from analyzer.cleaner import clean_sheet_data
from analyzer.formatter import write_new_format
from analyzer.parser import parse_response
from analyzer.reader import read_excel
from analyzer.sap_client import SAPAICoreClient
from analyzer.writer import write_output_excel

from analyzer_gui.config.settings import Settings
from analyzer_gui.core.config_factory import build_config
from analyzer_gui.i18n import t

# analyzer 各模块都用 logging.getLogger("analyzer"[.xxx]),挂到根 "analyzer" 即可捕获
_ANALYZER_LOGGER = "analyzer"
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


class _LogBridge(logging.Handler):
    """把 logging 记录转发给 GUI 的 on_log 回调。"""

    def __init__(self, on_log: Callable[[str], None]):
        super().__init__()
        self._on_log = on_log
        self.setFormatter(logging.Formatter(_LOG_FORMAT))

    def emit(self, record):
        try:
            self._on_log(self.format(record))
        except Exception:
            pass


class AnalyzeTask(threading.Thread):

    def __init__(self, files: List[Path], output_dir: Path, settings: Settings,
                 on_progress: Callable[[int, str], None],
                 on_log: Callable[[str], None],
                 on_done: Callable[[object], None],
                 on_failed: Callable[[Exception], None]):
        super().__init__(daemon=True)
        self.files = [Path(f) for f in files]
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_done = on_done
        self.on_failed = on_failed
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        logger = logging.getLogger(_ANALYZER_LOGGER)
        bridge = _LogBridge(self.on_log)
        prev_level = logger.level
        logger.setLevel(logging.INFO)
        logger.addHandler(bridge)
        try:
            self._run_pipeline(logger)
        except Exception as e:
            logging.getLogger("analyzer_gui").exception("analyze task failed")
            self.on_failed(e)
        finally:
            logger.removeHandler(bridge)
            logger.setLevel(prev_level)

    def _run_pipeline(self, logger):
        config = build_config(self.settings)
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        client = SAPAICoreClient(config)

        total = len(self.files)
        logger.info("Excel ファイルを %d 件検出しました。処理を開始します。", total)

        all_records = []
        success_count = 0
        failure_count = 0

        for idx, file_path in enumerate(self.files, 1):
            if self._cancel:
                self.on_log(t("log.cancelled"))
                break
            file_name = file_path.name
            base = int((idx - 1) / total * 100) if total else 0
            self.on_progress(base, f"[{idx}/{total}] " + t("phase.read"))
            logger.info("Processing file %d/%d: %s", idx, total, file_name)
            try:
                sheets = read_excel(file_path)
                cleaned_sheets = []
                for sheet in sheets:
                    cleaned = clean_sheet_data(sheet)
                    if cleaned is not None:
                        cleaned_sheets.append(cleaned)
                if not cleaned_sheets:
                    logger.warning(
                        "File %s: 全シートが清洗後に空のためスキップします。", file_name)
                    failure_count += 1
                    continue

                self.on_progress(base, f"[{idx}/{total}] " + t("phase.analyze"))
                tool_results = analyze_file(
                    client, cleaned_sheets, file_name,
                    phase1_head_rows=config.phase1_head_rows,
                    max_chunk_rows=config.max_chunk_rows,
                )

                records = []
                for tool_result in tool_results:
                    records.extend(parse_response(tool_result, file_name))
                all_records.extend(records)
                logger.info(
                    "File %s: %d 件のレコードを抽出しました。", file_name, len(records))

                if records:
                    self.on_progress(base, f"[{idx}/{total}] " + t("phase.format"))
                    first = records[0]
                    if_name_for_file = (first.if_name if hasattr(first, "if_name")
                                        else first.get("if_name", ""))
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
                            "File %s: 新フォーマット出力に失敗しました: %s",
                            file_name, fmt_exc)
                success_count += 1
            except Exception as exc:
                logger.error(
                    "File %s の処理中にエラーが発生しました: %s", file_name, exc)
                failure_count += 1
                continue

        if self._cancel:
            self.on_done(all_records)
            return

        self.on_progress(99, t("phase.output"))
        if all_records:
            output_path = write_output_excel(all_records, config.output_dir)
        else:
            output_path = "(レコードなし — 出力ファイルは生成されませんでした)"
            logger.warning("抽出レコードが 0 件のため、出力ファイルは生成されませんでした。")

        logger.info("=" * 60)
        logger.info("処理完了サマリー")
        logger.info("  対象ファイル数: %d", total)
        logger.info("  成功: %d", success_count)
        logger.info("  失敗: %d", failure_count)
        logger.info("  抽出レコード数: %d", len(all_records))
        logger.info("  出力ファイル: %s", output_path)
        logger.info("=" * 60)

        self.on_progress(100, t("phase.done"))
        self.on_done(all_records)
