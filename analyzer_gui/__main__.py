"""IF解析 GUI 程序入口:python -m analyzer_gui"""

from analyzer.runtime import app_data_dir
from analyzer_gui.config.settings import Settings
from analyzer_gui.ui.app import AnalyzerApp
from analyzer_gui.utils.logger import setup_logger


def main():
    settings = Settings.load()
    # 日志写到可写数据目录:开发态= 仓库根/output;打包后= exe 同级/output。
    log_file = str(app_data_dir() / "output" / "analyzer_gui.log")
    setup_logger(level=settings.log_level, log_file=log_file)
    app = AnalyzerApp(settings)
    app.mainloop()


if __name__ == "__main__":
    main()
