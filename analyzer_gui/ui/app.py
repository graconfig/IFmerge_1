"""CTk 主应用:侧栏(标题 + 日志 + 设置)+ 解析页。"""

import logging
from pathlib import Path

import customtkinter as ctk

from analyzer_gui.config.settings import Settings
from analyzer_gui.i18n import t, translator
from analyzer_gui.ui.dialogs.log_viewer import LogViewerDialog
from analyzer_gui.ui.dialogs.settings_dialog import SettingsDialog
from analyzer_gui.ui.pages.analyze_page import AnalyzePage
from analyzer_gui.utils.logger import setup_logger

logger = logging.getLogger("analyzer_gui.ui.app")


class AnalyzerApp(ctk.CTk):

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

        self.title(t("app.title"))
        self.geometry("1100x720")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_page()

    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, width=160, corner_radius=0)
        bar.grid(row=0, column=0, sticky="nsew")
        bar.grid_rowconfigure(1, weight=1)  # 把日志/设置推到底部

        ctk.CTkLabel(bar, text="IF解析", font=ctk.CTkFont(size=18, weight="bold")
                     ).grid(row=0, column=0, padx=16, pady=(16, 12))

        ctk.CTkButton(bar, text=t("sidebar.logs"), fg_color="gray",
                      command=self._open_logs
                      ).grid(row=2, column=0, padx=16, pady=(16, 4), sticky="ew")
        ctk.CTkButton(bar, text=t("sidebar.settings"), fg_color="gray",
                      command=self._open_settings
                      ).grid(row=3, column=0, padx=16, pady=(4, 16), sticky="ew")

    def _build_page(self):
        self.page = AnalyzePage(self, self)
        self.page.grid(row=0, column=1, sticky="nsew")

    def set_language(self, lang: str):
        """切换语言:持久化 + 实时重建侧栏/页面(当前选择/进度会清空)。"""
        translator.set_language(lang)
        for child in self.winfo_children():
            child.destroy()
        self.title(t("app.title"))
        self._build_sidebar()
        self._build_page()

    def _open_logs(self):
        LogViewerDialog(self, Path(self.settings.output_dir))

    def _open_settings(self):
        SettingsDialog(self, self.settings, on_saved=self._on_settings_saved)

    def _on_settings_saved(self, settings: Settings):
        self.settings = settings
        self.settings.save()                            # 持久化到 .env
        setup_logger(level=self.settings.log_level)      # 日志级别即时生效
        self.page.file_output.set_output_dir(self.page.output_dir())
