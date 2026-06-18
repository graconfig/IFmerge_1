"""文件输入块:选择文件夹,递归扫描其下所有 Excel。"""

from pathlib import Path
from tkinter import filedialog
from typing import Callable, List

import customtkinter as ctk

from analyzer_gui.i18n import t
from analyzer_gui.ui.utils.fs import find_excel_files


class FileInput(ctk.CTkFrame):

    def __init__(self, master, on_change: Callable[[List[Path]], None]):
        super().__init__(master)
        self._on_change = on_change
        self._files: List[Path] = []

        ctk.CTkLabel(self, text=t("input.title"), anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=8, pady=(6, 0))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        self.btn = ctk.CTkButton(row, text=t("input.choose_folder"), width=130,
                                 command=self._choose_folder)
        self.btn.pack(side="left")
        self.lbl_path = ctk.CTkLabel(row, text=t("input.unselected"), anchor="w")
        self.lbl_path.pack(side="left", fill="x", expand=True, padx=8)

    def _choose_folder(self):
        path = filedialog.askdirectory(title=t("input.dialog_title"))
        if not path:
            return
        folder = Path(path)
        self._files = find_excel_files(folder)
        self.lbl_path.configure(text=t("input.folder_fmt", path=folder))
        self._on_change(self._files)

    def files(self) -> List[Path]:
        return list(self._files)

    def set_enabled(self, enabled: bool):
        self.btn.configure(state="normal" if enabled else "disabled")
