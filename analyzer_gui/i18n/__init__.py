"""多语言(i18n):Translator 单例 + JSON locale + 用户配置持久化。"""

import json
from pathlib import Path

from analyzer.runtime import resource_path

# 打包后 locales 解压在 sys._MEIPASS/analyzer_gui/i18n/locales(由 ifanalyzer.spec 指定)。
_LOCALES_DIR = resource_path("analyzer_gui", "i18n", "locales")
_CONFIG_PATH = Path.home() / ".ifmerge" / "config.json"
_DEFAULT_LANG = "zh"
AVAILABLE = {"zh": "中文", "ja": "日本語", "en": "English"}


class Translator:
    def __init__(self, locales_dir=_LOCALES_DIR, config_path=_CONFIG_PATH,
                 default_lang=_DEFAULT_LANG):
        self._locales_dir = Path(locales_dir)
        self._config_path = Path(config_path)
        self._default = default_lang
        self._cache: dict[str, dict] = {}
        self._lang = self._load_saved_language()

    def current(self) -> str:
        return self._lang

    def available(self) -> dict:
        return dict(AVAILABLE)

    def t(self, key: str, **kwargs) -> str:
        s = self._locale(self._lang).get(key)
        if s is None:
            s = self._locale(self._default).get(key, key)
        if kwargs:
            try:
                return s.format(**kwargs)
            except Exception:
                return s
        return s

    def set_language(self, lang: str) -> None:
        if lang not in AVAILABLE:
            return
        self._lang = lang
        self._save_language(lang)

    def _locale(self, lang: str) -> dict:
        if lang not in self._cache:
            path = self._locales_dir / f"{lang}.json"
            try:
                self._cache[lang] = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self._cache[lang] = {}
        return self._cache[lang]

    def _load_saved_language(self) -> str:
        try:
            cfg = json.loads(self._config_path.read_text(encoding="utf-8"))
            if cfg.get("language") in AVAILABLE:
                return cfg["language"]
        except Exception:
            pass
        return self._default

    def _save_language(self, lang: str) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(
                json.dumps({"language": lang}), encoding="utf-8")
        except Exception:
            pass


translator = Translator()


def t(key: str, **kwargs) -> str:
    return translator.t(key, **kwargs)
