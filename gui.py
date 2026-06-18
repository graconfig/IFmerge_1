"""根目录便捷启动脚本(GUI)。等价于 `python -m analyzer_gui`。

命令行批处理入口仍是 `python main.py`。
"""

from analyzer_gui.__main__ import main

if __name__ == "__main__":
    main()
