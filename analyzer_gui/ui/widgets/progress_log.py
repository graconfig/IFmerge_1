"""进度 / 日志块:进度条 + 阶段文本 + 滚动日志。"""

import customtkinter as ctk

from analyzer_gui.i18n import t


class ProgressLog(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        ctk.CTkLabel(self, text=t("progress.title"), anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=8, pady=(6, 0))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=4)
        self.bar = ctk.CTkProgressBar(top)
        self.bar.set(0)
        self.bar.pack(side="left", fill="x", expand=True)
        self.lbl_phase = ctk.CTkLabel(top, text=t("progress.idle"), width=180, anchor="w")
        self.lbl_phase.pack(side="left", padx=8)

        self.log = ctk.CTkTextbox(self, height=160)
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log.configure(state="disabled")

    def reset(self):
        self.bar.set(0)
        self.lbl_phase.configure(text=t("progress.idle"))
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def set_progress(self, percent: int, phase: str):
        self.bar.set(max(0.0, min(1.0, percent / 100.0)))
        if phase:
            self.lbl_phase.configure(text=phase)

    def append_log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_finished(self):
        self.bar.set(1.0)
        self.lbl_phase.configure(text=t("progress.done"))

    def set_failed(self):
        self.lbl_phase.configure(text=t("progress.failed"))
