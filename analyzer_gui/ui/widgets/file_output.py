"""文件输出块:显示输出目录路径 + 打开文件夹按钮。"""

from pathlib import Path

import customtkinter as ctk

from analyzer_gui.i18n import t
from analyzer_gui.ui.utils.fs import open_folder


class FileOutput(ctk.CTkFrame):

    def __init__(self, master, output_dir: Path):
        super().__init__(master)
        self._output_dir = Path(output_dir)

        ctk.CTkLabel(self, text=t("output.title"), anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=8, pady=(6, 0))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(row, text=t("output.open"), width=130,
                      command=self._open).pack(side="left")
        self.lbl = ctk.CTkLabel(row, text=t("output.prefix", dir=self._output_dir), anchor="w")
        self.lbl.pack(side="left", fill="x", expand=True, padx=8)

    def _open(self):
        open_folder(self._output_dir)

    def set_output_dir(self, output_dir: Path):
        self._output_dir = Path(output_dir)
        self.lbl.configure(text=t("output.prefix", dir=self._output_dir))
