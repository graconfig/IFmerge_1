"""页面抽象基类:文件输入 + 文件输出 + 执行 + 进度日志,统一线程编排。"""

from datetime import datetime
from pathlib import Path
from typing import List

import customtkinter as ctk

from analyzer_gui.i18n import t
from analyzer_gui.ui.widgets.file_input import FileInput
from analyzer_gui.ui.widgets.file_output import FileOutput
from analyzer_gui.ui.widgets.progress_log import ProgressLog


class BasePage(ctk.CTkFrame):
    """子类需重写 run_button_text() / output_dir() / log_kind() / create_task(files)。"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._task = None
        self._files: List[Path] = []
        self._log_lines: List[str] = []

        self.file_input = FileInput(self, on_change=self._on_selection_change)
        self.file_input.pack(fill="x", padx=10, pady=(10, 4))

        self.file_output = FileOutput(self, output_dir=self.output_dir())
        self.file_output.pack(fill="x", padx=10, pady=4)

        exec_frame = ctk.CTkFrame(self)
        exec_frame.pack(fill="x", padx=10, pady=4)
        self.btn_run = ctk.CTkButton(exec_frame, text=self.run_button_text(),
                                     command=self._start, state="disabled")
        self.btn_run.pack(side="left", padx=8, pady=8)
        self.btn_cancel = ctk.CTkButton(exec_frame, text=t("page.cancel"), width=80,
                                        command=self._cancel, state="disabled")
        self.btn_cancel.pack(side="left", pady=8)

        self.progress_log = ProgressLog(self)
        self.progress_log.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    # ── 子类重写 ──
    def run_button_text(self) -> str:
        raise NotImplementedError

    def output_dir(self) -> Path:
        raise NotImplementedError

    def log_kind(self) -> str:
        raise NotImplementedError

    def create_task(self, files: List[Path]):
        raise NotImplementedError

    # ── 内部 ──
    def _on_selection_change(self, files: List[Path]):
        self._files = files
        self.btn_run.configure(state="normal" if files else "disabled")

    def _start(self):
        if not self._files:
            return
        self._log_lines = []
        self.progress_log.reset()
        self._set_running(True)
        self._task = self.create_task(self._files)
        self._task.start()

    def _save_log(self):
        if not self._log_lines:
            return
        log_dir = self.output_dir() / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = log_dir / f"{self.log_kind()}_{ts}.log"
            path.write_text("\n".join(self._log_lines) + "\n", encoding="utf-8")
            self.progress_log.append_log(t("log.saved", path=path))
        except Exception as e:
            self.progress_log.append_log(t("log.save_fail", error=e))

    def _cancel(self):
        if self._task is not None:
            self._task.cancel()

    def _set_running(self, running: bool):
        self.btn_run.configure(state="disabled" if running else "normal")
        self.btn_cancel.configure(state="normal" if running else "disabled")
        self.file_input.set_enabled(not running)

    # ── 线程安全回调(经 after 调度回主线程)──
    def _cb_progress(self, percent: int, phase: str):
        self.after(0, lambda: self.progress_log.set_progress(percent, phase))

    def _cb_log(self, msg: str):
        def add():
            self._log_lines.append(msg)
            self.progress_log.append_log(msg)
        self.after(0, add)

    def _cb_done(self, result):
        def finish():
            self.progress_log.set_finished()
            self._save_log()
            self._set_running(False)
        self.after(0, finish)

    def _cb_failed(self, exc: Exception):
        def fail():
            self.progress_log.set_failed()
            msg = t("log.failed", type=type(exc).__name__, error=exc)
            self._log_lines.append(msg)
            self.progress_log.append_log(msg)
            self._save_log()
            self._set_running(False)
        self.after(0, fail)
