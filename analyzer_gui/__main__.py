"""IF解析 GUI 程序入口:python -m analyzer_gui"""

from analyzer_gui.config.settings import Settings
from analyzer_gui.ui.app import AnalyzerApp
from analyzer_gui.utils.logger import setup_logger


def main():
    settings = Settings.load()
    setup_logger(level=settings.log_level)
    app = AnalyzerApp(settings)
    app.mainloop()


if __name__ == "__main__":
    main()
