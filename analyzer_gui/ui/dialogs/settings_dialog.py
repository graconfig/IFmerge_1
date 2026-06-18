"""设置对话框(CTkToplevel):精简项 + 折叠高级设置。"""

from tkinter import messagebox

import customtkinter as ctk

from analyzer_gui.config.settings import Settings
from analyzer_gui.i18n import AVAILABLE, t, translator


class SettingsDialog(ctk.CTkToplevel):

    def __init__(self, master, settings: Settings, on_saved):
        super().__init__(master)
        self.settings = settings
        self._on_saved = on_saved
        self.title(t("settings.title"))
        self.geometry("560x600")
        self.grab_set()
        self._advanced_visible = False
        self._build()

    def _row(self, parent, label, value, show=None):
        ctk.CTkLabel(parent, text=label, anchor="w",
                     text_color=("gray10", "gray90")).pack(fill="x", padx=12, pady=(8, 0))
        entry = ctk.CTkEntry(parent, show=show)
        entry.insert(0, value or "")
        entry.pack(fill="x", padx=12)
        return entry

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # 语言(改动即实时切换整个 UI)
        ctk.CTkLabel(scroll, text=t("settings.language"), anchor="w",
                     text_color=("gray10", "gray90")).pack(fill="x", padx=12, pady=(8, 0))
        self._lang_codes = list(AVAILABLE.keys())
        self._lang_names = list(AVAILABLE.values())
        self.opt_lang = ctk.CTkOptionMenu(
            scroll, values=self._lang_names, command=self._on_language_change)
        self.opt_lang.set(AVAILABLE[translator.current()])
        self.opt_lang.pack(fill="x", padx=12)

        # 基本:AI Core Base URL + 测试连接
        self.ed_base = self._row(scroll, t("settings.aicore_base_url"),
                                 self.settings.aicore_base_url)
        ctk.CTkButton(scroll, text=t("settings.test_conn"), command=self._test).pack(
            anchor="w", padx=12, pady=6)

        # 折叠高级
        self.btn_adv = ctk.CTkButton(scroll, text=t("settings.advanced_show"),
                                     fg_color="transparent", anchor="w",
                                     text_color=("gray10", "gray90"),
                                     hover_color=("gray80", "gray30"),
                                     command=self._toggle_advanced)
        self.btn_adv.pack(fill="x", padx=12, pady=(12, 0))
        self.adv = ctk.CTkFrame(scroll)
        self.ed_auth = self._row(self.adv, t("settings.aicore_auth_url"),
                                 self.settings.aicore_auth_url)
        self.ed_cid = self._row(self.adv, t("settings.aicore_client_id"),
                                self.settings.aicore_client_id)
        self.ed_secret = self._row(self.adv, t("settings.aicore_client_secret"),
                                   self.settings.aicore_client_secret, show="*")
        self.ed_rg = self._row(self.adv, t("settings.aicore_resource_group"),
                               self.settings.aicore_resource_group)
        self.ed_dep = self._row(self.adv, t("settings.aicore_deployment_id"),
                                self.settings.aicore_deployment_id)
        self.ed_output = self._row(self.adv, t("settings.output_dir"),
                                   self.settings.output_dir)
        self.ed_template = self._row(self.adv, t("settings.template"),
                                     self.settings.template_path)
        self.ed_reference = self._row(self.adv, t("settings.reference"),
                                      self.settings.reference_path)
        self.ed_phase1 = self._row(self.adv, t("settings.phase1"),
                                   str(self.settings.phase1_head_rows))
        self.ed_chunk = self._row(self.adv, t("settings.chunk"),
                                  str(self.settings.max_chunk_rows))
        self.ed_log = self._row(self.adv, t("settings.log_level"),
                                self.settings.log_level)

        # 按钮
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(btns, text=t("settings.save"), command=self._save).pack(
            side="right", padx=4)
        ctk.CTkButton(btns, text=t("settings.cancel"), command=self.destroy,
                      fg_color="gray").pack(side="right", padx=4)

    def _on_language_change(self, display_name: str):
        code = self._lang_codes[self._lang_names.index(display_name)]
        self.destroy()
        self.master.set_language(code)

    def _toggle_advanced(self):
        self._advanced_visible = not self._advanced_visible
        if self._advanced_visible:
            self.adv.pack(fill="x", padx=12, pady=6)
            self.btn_adv.configure(text=t("settings.advanced_hide"))
        else:
            self.adv.pack_forget()
            self.btn_adv.configure(text=t("settings.advanced_show"))

    def _test(self):
        from analyzer.config import AppConfig
        from analyzer.sap_client import SAPAICoreClient
        try:
            cfg = AppConfig(
                auth_url=self.ed_auth.get(), client_id=self.ed_cid.get(),
                client_secret=self.ed_secret.get(), base_url=self.ed_base.get(),
                resource_group=self.ed_rg.get() or "default",
                deployment_id=self.ed_dep.get(),
                input_dir="", output_dir="", phase1_head_rows=30, max_chunk_rows=100,
                template_path="", reference_path="",
            )
            SAPAICoreClient(cfg)._get_access_token()
            messagebox.showinfo(t("settings.test_conn"), t("settings.test_ok"))
        except Exception as e:
            messagebox.showwarning(t("settings.test_conn"),
                                   t("settings.test_fail", error=e))

    def _save(self):
        s = self.settings
        s.aicore_base_url = self.ed_base.get()
        s.aicore_auth_url = self.ed_auth.get()
        s.aicore_client_id = self.ed_cid.get()
        s.aicore_client_secret = self.ed_secret.get()
        s.aicore_resource_group = self.ed_rg.get()
        s.aicore_deployment_id = self.ed_dep.get()
        s.output_dir = self.ed_output.get()
        s.template_path = self.ed_template.get()
        s.reference_path = self.ed_reference.get()
        s.phase1_head_rows = int(self.ed_phase1.get())
        s.max_chunk_rows = int(self.ed_chunk.get())
        s.log_level = self.ed_log.get()
        self._on_saved(s)
        self.destroy()
