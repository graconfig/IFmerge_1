"""日志查看器:列出 output/parse/logs 与 output/merge/logs 下的 *.log 并查看。"""

from pathlib import Path

import customtkinter as ctk

from analyzer_gui.i18n import t


class LogViewerDialog(ctk.CTkToplevel):

    def __init__(self, master, output_dir: Path):
        super().__init__(master)
        self.title(t("logviewer.title"))
        self.geometry("840x560")
        self.grab_set()
        base = Path(output_dir)
        # GUI 每次执行的日志(base_page 保存)+ analyzer 自身的 analyzer.log
        self._dirs = [base / "logs", base]
        self._files = self._scan()
        self._build()

    def _scan(self) -> list[Path]:
        files: list[Path] = []
        for d in self._dirs:
            if d.is_dir():
                files.extend(d.glob("*.log"))
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(self, width=280, label_text=t("logviewer.history"))
        left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.text = ctk.CTkTextbox(self)
        self.text.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        self.text.configure(state="disabled")

        if not self._files:
            ctk.CTkLabel(left, text=t("logviewer.empty"), text_color="gray").pack(pady=8)
            return
        for p in self._files:
            ctk.CTkButton(left, text=p.name, anchor="w", fg_color="transparent",
                          text_color=("gray10", "gray90"),
                          hover_color=("gray80", "gray30"),
                          command=lambda fp=p: self._show(fp)).pack(fill="x", pady=2)
        self._show(self._files[0])

    def _show(self, path: Path):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            content = t("logviewer.read_fail", error=e)
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content)
        self.text.configure(state="disabled")
