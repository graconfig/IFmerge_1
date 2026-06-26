# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 —— IF解析 桌面 GUI(Windows)。

构建(在 Windows 上,仓库根目录执行):
    pip install -r requirements.txt
    pip install pyinstaller
    pyinstaller ifanalyzer.spec

产物:dist/IFAnalyzer/IFAnalyzer.exe(onedir,默认)。
切换单文件:见文件末尾 onefile 说明。

入口:gui.py(等价于 `python -m analyzer_gui`,即桌面 GUI;命令行批处理
入口 main.py 不打包)。

资源约定(与 analyzer/runtime.py 的 resource_path() 对应):
    prompts.yaml                              -> <bundle>/prompts.yaml
    reference/IF抽出_新フォーマット.xlsx       -> <bundle>/reference/IF抽出_新フォーマット.xlsx
    reference/本社EBS現行IF一覧.xlsx           -> <bundle>/reference/本社EBS現行IF一覧.xlsx
    analyzer_gui/i18n/locales/*.json          -> <bundle>/analyzer_gui/i18n/locales/
可写文件(.env / input / output / 日志)运行时写到 exe 同级目录(app_data_dir())。
"""

import os
from PyInstaller.utils.hooks import collect_data_files

# SPECPATH 由 PyInstaller 注入,指向本 spec 所在目录(= 仓库根)。
ROOT = SPECPATH

# ---- 只读资源:打进 bundle,保持 resource_path() 期望的相对结构 ----
datas = [
    (os.path.join(ROOT, "prompts.yaml"), "."),
]

# reference 下的模板/参照 Excel(只读;运行时被复制到 output 后再编辑)。
_reference_dir = os.path.join(ROOT, "reference")
for _name in os.listdir(_reference_dir):
    if _name.lower().endswith((".xlsx", ".xlsm", ".xls")):
        datas.append((os.path.join(_reference_dir, _name), "reference"))

# i18n 语言文件(逐个收集,目标目录与 resource_path 对应)
_locales_dir = os.path.join(ROOT, "analyzer_gui", "i18n", "locales")
for _name in os.listdir(_locales_dir):
    if _name.endswith(".json"):
        datas.append((os.path.join(_locales_dir, _name),
                      os.path.join("analyzer_gui", "i18n", "locales")))

# customtkinter 自带主题/字体等数据文件 —— 不收集会导致界面崩溃(最常见的坑)。
datas += collect_data_files("customtkinter")

# openpyxl / xlrd / requests 由 PyInstaller 内置 hook 处理,通常无需手动添加。
# 若运行时报 "No module named ..." 再按需补到这里。
hiddenimports = []

# ---- 可选图标:存在则使用(放 assets/IFAnalyzer.ico) ----
_icon = os.path.join(ROOT, "assets", "IFAnalyzer.ico")
icon = _icon if os.path.exists(_icon) else None


a = Analysis(
    [os.path.join(ROOT, "gui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 测试/构建期依赖不进运行时包,减小体积。
    excludes=["pytest", "hypothesis", "_pytest", "pluggy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,        # onedir:二进制交给 COLLECT
    name="IFAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                # GUI 模式,不弹控制台黑窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="IFAnalyzer",
)

# ---- 切换为单文件(onefile)发布 ----
# 注释掉上面的 exe(exclude_binaries=True) 与整个 COLLECT,改用:
#
# exe = EXE(
#     pyz, a.scripts, a.binaries, a.datas, [],
#     name="IFAnalyzer", debug=False, strip=False, upx=True,
#     console=False, icon=icon,
# )
#
# 注意:onefile 启动较慢(每次解压到临时目录),建议先用 onedir 调通再切换。
