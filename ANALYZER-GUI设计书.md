# ANALYZER-GUI 设计书

> 版本：v1.0
> 工程路径：`/data/HuangCX/IFmerge_1/`
> 编写日期：2026-06-25（与 `feat/analyzer-gui` 分支实现对齐）

---

## 1. 概述

本地桌面端，作为 Excel 接口设计书（IF設計書）**解析工具**的图形界面。一个程序内含**解析**单一功能：选含 Excel 接口设计书的文件夹 → 本地读取/清洗 → 二阶段 AI 分析（SAP AI Core）→ 产出 **抽出結果 Excel** + **新フォーマット Excel**。

**职责**：
1. 选含接口设计书 Excel 的文件夹（递归扫描 `.xlsx/.xls/.xlsm`）。
2. 本地读取（删除线/对角叉检测）→ 清洗（删除线置空、去空行）。
3. 调 SAP AI Core Converse + Tool Calling 做二阶段分析（Phase1 识别固定信息与数据シート，Phase2 分块抽出项目）。
4. 产出抽出結果 Excel（汇总 8 列）+ 每文件一个新フォーマット Excel（套参考主数据）。

**与命令行版的关系**：仓库已有命令行批处理入口 `main.py`（`python main.py`，读 `input/` 目录、走环境变量配置）。本 GUI 是在其之上叠加的可视化层，**复用同一套 `analyzer/` 核心模块**，编排逻辑镜像自 `main.py`。

**与参考工程 `ifmerge-gui` 的关键差异**：

| 维度 | `ifmerge-gui`（参考） | 本工程 `analyzer_gui` |
|---|---|---|
| 功能 | 解析 + 合并 两大功能（侧栏切换） | **仅解析**（单页） |
| 后端 | CAP 后端 HTTP API（`/analyze`、`/merge`） | **进程内直调** `analyzer/` 包 + SAP AI Core |
| 任务模型 | 提交 Job → 轮询 → 取结果 | **同步流水线**（线程内串行处理每个文件，无 Job 轮询） |
| 鉴权 | XSUAA / Client Credentials | SAP AI Core OAuth2 `client_credentials` |
| 产物 | 5 类（抽出/新格式/グルーピング/矩阵/模板） | **2 类**（抽出結果 + 新フォーマット） |

**技术栈**：

| 项 | 选择 |
|---|---|
| 语言 | Python 3.10+ |
| UI 框架 | **CustomTkinter ≥ 5.2** |
| 后台并发 | **`threading.Thread` + 回调**（经 `widget.after()` 调度回主线程） |
| Excel 读写 | openpyxl ≥ 3.1（xlsx/xlsm）+ xlrd ≥ 1.2（xls） |
| HTTP | requests（直连 SAP AI Core） |
| 提示词 | `prompts.yaml`（Phase1/Phase2 模板，带内置回退） |
| 配置 | python-dotenv（读写仓库根 `.env`） |
| 多语言 | 自研轻量 i18n（JSON locale，中/日/英） |
| 打包 | PyInstaller（Windows .exe，后续） |

---

## 2. 项目结构

```
IFmerge_1/
├── main.py                        ← 命令行批处理入口（python main.py，读 input/）
├── gui.py                         ← GUI 便捷启动（= python -m analyzer_gui）
├── run.bat                        ← Windows 批处理（CLI 模式）
├── prompts.yaml                   ← Phase1/Phase2 提示词模板（可配置，带内置回退）
├── requirements.txt
├── .env                           ← SAP AI Core 凭证 + 路径 + AI 参数（设置弹窗写回这里）
│
├── analyzer_gui/                  ← CustomTkinter GUI 层（本分支新增）
│   ├── __main__.py                入口：Settings.load → setup_logger → AnalyzerApp.mainloop
│   │
│   ├── config/
│   │   └── settings.py            .env 加载 + 写回（固定仓库根 .env）
│   ├── core/
│   │   └── config_factory.py      用 GUI Settings 构造 analyzer.AppConfig（设置即权威来源）
│   │
│   ├── i18n/                      ← 多语言
│   │   ├── __init__.py            Translator 单例 + 模块级 t()
│   │   └── locales/{zh,ja,en}.json  key → 文本（三语 key 一致，约 65 个 key）
│   │
│   ├── ui/                        ← CustomTkinter 界面层
│   │   ├── app.py                 AnalyzerApp：侧栏（标题 + 日志 + 设置）+ 解析页 + set_language
│   │   ├── pages/
│   │   │   ├── base_page.py       通用页（四行块 + 线程回调经 after 调度 + 日志落盘）
│   │   │   └── analyze_page.py    解析页（绑定 AnalyzeTask）
│   │   ├── widgets/
│   │   │   ├── file_input.py      文件夹选择（递归找 Excel）
│   │   │   ├── file_output.py     输出路径 + 打开文件夹
│   │   │   └── progress_log.py    进度条（0–1）+ 滚动日志框
│   │   ├── dialogs/
│   │   │   ├── settings_dialog.py 设置（CTkToplevel，精简 + 折叠高级 + 语言）
│   │   │   └── log_viewer.py      历史执行日志查看器
│   │   ├── tasks/
│   │   │   └── analyze_task.py    解析后台任务（threading，编排镜像 main.py）
│   │   └── utils/
│   │       └── fs.py              递归扫描 Excel + 跨平台打开文件夹
│   │
│   └── utils/
│       └── logger.py             GUI 日志器（控制台 + output/analyzer_gui.log 双输出）
│
├── analyzer/                      ← 业务核心（框架无关，CLI 与 GUI 共用）
│   ├── config.py                  AppConfig + load_config（环境变量加载，CLI 用）
│   ├── scanner.py                 扫描 input 目录 Excel（非递归，CLI 用）
│   ├── reader.py                  读取 Excel（删除线 / 对角叉 / 富文本检测）
│   ├── cleaner.py                 清洗（删除线置空、去空行）
│   ├── ai_analyzer.py             二阶段 AI 分析（Phase1/Phase2）+ prompts.yaml 加载
│   ├── sap_client.py              SAP AI Core Converse + Tool Calling 客户端
│   ├── parser.py                  Tool Call 响应 → InterfaceRecord（14 字段）
│   ├── writer.py                  抽出結果 Excel（8 列）
│   ├── formatter.py               新フォーマット Excel（套参考主数据合成）
│   ├── logger.py                  analyzer 自身日志器（日语，CLI 用）
│   └── test_*.py                  pytest 单元测试
│
├── reference/                     ← 随分发的参考主数据（2 个）
│   ├── IF抽出_新フォーマット.xlsx
│   └── 本社EBS現行IF一覧.xlsx
├── output/                        ← 默认输出（extracted/ + formatted/ + logs/）
└── docs/                          ← 规格 / 实现计划文档
```

> 复用边界：`analyzer_gui/` 不复制业务逻辑，全部委托给 `analyzer/`。GUI 仅提供：① CustomTkinter 界面；② 线程编排 + 进度/日志回调；③ i18n；④ `.env` 设置弹窗与持久化；⑤ 递归文件夹扫描（`main.py` 是非递归扫 `input/`，GUI 改为用户选文件夹后递归）。

---

## 3. 布局

### 3.1 主窗口（侧栏 + 右侧四行块）

```
┌─────────────┬──────────────────────────────────────────────┐
│  IF解析      │  ┌── 文件输入 ─────────────────────────────┐ │
│             │  │ 📁 选择文件夹    📁 C:\...\接口设计书       │ │
│             │  └─────────────────────────────────────────┘ │
│             │  ┌── 文件输出 ─────────────────────────────┐ │
│             │  │ 📂 打开文件夹   输出: output               │ │
│             │  └─────────────────────────────────────────┘ │
│             │  ┌── 执行 ─────────────────────────────────┐ │
│             │  │ [▶ 开始解析]          [取消]               │ │
│             │  └─────────────────────────────────────────┘ │
│             │  ┌── 进度 / 日志 ──────────────────────────┐ │
│             │  │ ▓▓▓▓▓▓░░░░ 60%  [3/5] AI 解析中           │ │
│  📜 日志     │  │ ──────────────────────────────────────── │ │
│  ⚙ 设置      │  │ 正在处理文件 3/5: c.xlsx ...               │ │
│             │  └─────────────────────────────────────────┘ │
└─────────────┴──────────────────────────────────────────────┘
```

- **左侧栏**（`width=160`，`corner_radius=0`）：品牌名「IF解析」（粗体 18pt）置顶；底部「📜 日志」「⚙ 设置」两个灰色按钮（`grid_rowconfigure(1, weight=1)` 把它们推到底部）。
  > 因为只有解析一个功能，侧栏**没有页面导航按钮**（区别于参考工程的「解析/合并」切换）。
- **右侧**：自上而下四个横向行块 —— 文件输入 / 文件输出 / 执行 / 进度·日志。
- **无结果预览**：结果只落地为 Excel，用「打开文件夹」查看。

### 3.2 窗口尺寸

| 项 | 值 |
|---|---|
| 主窗口初始尺寸 | 1100 × 720 |
| 设置弹窗 | 560 × 600 |
| 日志查看器 | 840 × 560 |
| 外观主题 | 跟随系统（亮/暗），文字颜色用 `(亮色, 暗色)` 二元组自适应 |

---

## 4. 界面组件设计

### 4.1 FileInput（widget，文件输入块）

| 控件 | 行为 |
|---|---|
| 「📁 选择文件夹」按钮 | `tkinter.filedialog.askdirectory` 选文件夹 |
| 路径标签 | 显示所选文件夹（`📁 {path}`） |

选中后**递归扫描**该文件夹及子目录下全部 `*.xlsx/*.xls/*.xlsm`（`Path.rglob`，跳过 `~$` 临时锁文件，按路径排序），归一为 `list[Path]` 经 `on_change` 回调上报页面。选中即启用「开始解析」按钮。
> 注：tkinter 原生对话框无法在同一弹框同时选文件夹和文件，故只保留文件夹选择。

### 4.2 FileOutput（widget，文件输出块）

显示当前输出目录（默认 `output`）+「📂 打开文件夹」按钮（跨平台：Windows `os.startfile` / macOS `open` / Linux `xdg-open`；目录不存在先创建）。设置里改了输出目录，保存后由 `app._on_settings_saved` 调 `set_output_dir` 刷新。

### 4.3 ProgressLog（widget，进度/日志块）

| 控件 | 说明 |
|---|---|
| 进度条 | `CTkProgressBar`，值域 **0.0–1.0**（后台传 0–100，除以 100，并 clamp 到 [0,1]） |
| 阶段标签 | 显示当前阶段文本（如 `[3/5] AI 解析中`），宽 180 |
| 日志框 | `CTkTextbox`（高 160），只追加、自动滚到底、常态 `disabled` 防误编辑 |

进度阶段：`待机 → 读取中 → AI 解析中 → 新格式输出`（循环每文件）`→ 结果输出 → 完成`；失败显示「✗ 失败」。

### 4.4 SettingsDialog（CTkToplevel）

`CTkScrollableFrame` 承载，`grab_set()` 模态。

| 区 | 项 | 控件 | 说明 |
|---|---|---|---|
| **主区** | 语言 / Language | `CTkOptionMenu` | 中文 / 日本語 / English，**选中即实时切换**（关弹窗 → `app.set_language`） |
|  | AI Core Base URL | `CTkEntry` | |
|  | 测试连接 | `CTkButton` | 用当前输入构造 `AppConfig` 调 `SAPAICoreClient._get_access_token()`，弹消息框 |
| **折叠「▸ 高级设置」** | AI Core Auth URL / Client ID / Client Secret（密文）/ Resource Group / Deployment ID | `CTkEntry` | SAP AI Core 凭证 |
|  | 输出目录 / 抽取模板 xlsx / 参考主数据 xlsx | `CTkEntry` | 路径 |
|  | Phase1 头部行数 / Chunk 最大行数 / 日志级别 | `CTkEntry` | AI 参数与运行 |
| **底部** | 保存 / 取消 | `CTkButton` | |

- **保存即持久化**：`_save` 收集所有字段 → `on_saved` 回调 → `Settings.save()` 用 `dotenv.set_key` 逐键写回**仓库根 `.env`**（固定路径，见 §9），重启保留。
- **日志级别即时生效**：保存后 `app` 重调 `setup_logger(level=...)`。
- **无「大模型选择」**：模型由 SAP AI Core 的 `deployment_id` 决定（见 §7.4），前端不暴露模型选择。

### 4.5 LogViewerDialog（CTkToplevel，侧栏「📜 日志」）

扫描两处目录的 `*.log`：① `output/logs/`（GUI 每次执行落盘的 `analyze_<ts>.log`）；② `output/`（`analyzer` 自身的 `analyzer.log`）。按修改时间倒序在左列列出，点击在右侧 `CTkTextbox` 查看内容。无日志时显示占位文案。

---

## 5. 线程模型

### 5.1 总体结构

CustomTkinter / tkinter **非线程安全**，后台线程不得直接操作控件。

```
┌────────── Main UI Thread (Tk mainloop) ──────────┐
│  渲染界面 / 响应操作 / 经 after() 应用回调结果       │
└──────────────┬─────────────────────────────────────┘
               │ task.start()
               ▼
   ┌──────────────────────────────────────────────┐
   │  AnalyzeTask (threading.Thread, daemon=True)   │
   │  ────────────────────────────────────────────  │
   │  进程内串行流水线（编排镜像 main.py）：           │
   │   build_config → SAPAICoreClient               │
   │   for each file:                                │
   │     read_excel → clean_sheet_data               │
   │     → analyze_file(Phase1/Phase2)               │
   │     → parse_response → write_new_format         │
   │   → write_output_excel(汇总)                     │
   │  通过回调上报：                                  │
   │   on_progress(percent, phase) / on_log(msg)     │
   │   on_done(records) / on_failed(exc)             │
   └──────────────────────────────────────────────┘
```

- **回调封送**：`BasePage` 注册的 `_cb_*` 回调内部统一 `self.after(0, lambda: …)`，把所有 UI 更新调度回主线程。
- **同步流水线，无 Job 轮询**：与参考工程不同，AI 调用是线程内同步 `requests` 调用（`SAPAICoreClient.converse_with_tools`）。进度由「当前文件序号 / 总数」推算（`base = (idx-1)/total*100`），不依赖远端 Job 进度。
- **进度换算**：`CTkProgressBar` 值域 0.0–1.0；后台传 0–100，`ProgressLog.set_progress` 除以 100。结果输出阶段固定 99%，完成 100%。
- **逐文件容错**：单文件读取/分析/输出异常被捕获，记 `failure_count` 并 `continue`，不影响其余文件（与 `main.py` 一致，Req 1.4/3.4）。新フォーマット 输出失败单独降级（仅告警，不算整文件失败）。

### 5.2 任务回调

| 回调 | 参数 | 用途 |
|---|---|---|
| `on_progress` | `(int percent, str phase)` | 进度条 + 阶段标签 |
| `on_log` | `(str message)` | 日志框追加（并累积到 `_log_lines`，结束时落盘） |
| `on_done` | `(list records)` | 标记完成、保存日志、恢复按钮 |
| `on_failed` | `(Exception)` | 标记失败、记录 `✗ 失败: <类型>: <消息>`、保存日志 |

### 5.3 取消语义

- `AnalyzeTask` 持有 `_cancel` 标志；`cancel()` 置位；流水线**在每个文件循环开头检查** `_cancel`，置位则记「已被用户取消」并跳出循环，把**已处理的记录**走 `on_done` 落地。
- 取消粒度为**文件级**：正在进行的单文件 AI 调用（可能耗时较长）**不会被中断**，会跑完当前文件后才停。

### 5.4 并发控制

| 规则 | 实现 |
|---|---|
| 运行中禁用「开始解析」、启用「取消」、禁用文件选择 | `BasePage._set_running` |
| 主线程不阻塞 | 所有 Excel/HTTP 在 `Thread` 内 |
| 切换语言会重建 UI | `app.set_language` 销毁并重建侧栏/页面，**清空当前已选文件与进度**（已知取舍） |

---

## 6. 错误处理

### 6.1 错误分类与 UI 行为

| 错误类型 | 触发 | UI 行为 |
|---|---|---|
| **文件读取错误** | Excel 损坏 / 无法解析 | 单文件 `try/except` → 日志记 `文件 X 处理中发生错误` + `failure_count++` + 跳过 |
| **清洗后为空** | 全 sheet 删除/空行后无数据 | 日志记「所有 sheet 清洗后为空，跳过」+ `failure_count++` |
| **认证失败** | SAP AI Core 凭证错误 | `_get_access_token` 抛 `トークン取得失敗: <status>` → 任务 `on_failed` 红字 |
| **API 调用失败** | Converse 非 200 | `API呼び出し失敗: <status> - <text>` → `on_failed` |
| **抽出记录为 0** | AI 未抽出任何项目 | 不生成抽出結果 Excel，日志记「抽出记录为 0 件」，输出路径标 `-` |
| **新フォーマット失败** | 参考主数据缺失 / 模板异常 | 单文件降级：仅日志告警，不影响抽出結果汇总 |
| **必填字段缺失** | `document_number`/`if_name` 空 | `parser` 记 warning，缺失字段填空串，记录仍保留 |

### 6.2 失败收口

- 任务级未捕获异常统一在 `AnalyzeTask.run` 的 `try/except` 收口 → `on_failed`。
- `on_failed` / `on_done` 都会触发 `_save_log()` 把本次完整日志写入 `output/logs/analyze_<ts>.log`。

---

## 7. 后端调用映射（进程内 + SAP AI Core）

> 区别于参考工程的 CAP HTTP 映射：本工程 GUI **直接在进程内调用 `analyzer/` 函数**，再由 `analyzer/sap_client.py` 直连 SAP AI Core。下面同时给出「GUI 动作 → 内部调用」与「内部 → SAP AI Core HTTP」两层。

### 7.1 用户操作 → 内部调用

| GUI 动作 | 内部调用链 |
|---|---|
| 选择文件夹 | `fs.find_excel_files`（递归 rglob） |
| 测试连接 | `SAPAICoreClient(cfg)._get_access_token()`（OAuth2 取 token） |
| 开始解析（每文件） | `read_excel` → `clean_sheet_data` → `analyze_file` → `parse_response` → `write_new_format` |
| 解析收尾 | `write_output_excel(all_records)`（汇总抽出結果） |
| 打开文件夹 | `fs.open_folder`（跨平台） |

### 7.2 解析数据流（重要）

```
文件夹(递归 Excel)
  └─ read_excel(file)                     读取，含删除线/对角叉/富文本检测
       └─ clean_sheet_data(sheet)         删除线置空 + 去空行 → CleanedSheet[]
            └─ analyze_file(...)          二阶段 AI（见 §7.3）→ tool_results[]
                 └─ parse_response(...)   → InterfaceRecord[]（14 字段）
                      ├─ write_new_format(...)   每文件 1 个新フォーマット
                      └─ all_records.extend(...)
write_output_excel(all_records)           汇总 1 个抽出結果（8 列）
```

- **InterfaceRecord 共 14 字段**：`document_number / if_name / ebs_table_name / ebs_table_id / item_id / item_name / digit_count`（7 必备）+ `item_description / data_type / digit_decimal / dev_type / is_key / required / remarks`（6 选填，默认空串）。
- **抽出結果 Excel 只落 8 列**（含 No.，见 §8）；新フォーマット 用全部记录套模板。

### 7.3 二阶段 AI 分析（`analyzer/ai_analyzer.py`）

| 阶段 | 输入 | 目的 |
|---|---|---|
| **Phase 1** | 各 sheet 先头 `phase1_head_rows`（默认 30）行文本 | 识别固定信息（`document_number` / `if_name`）+ 含数据项目的シート + 列结构（数据起始行、各列号） |
| **Phase 2** | 数据シート行数据，按 `max_chunk_rows`（默认 100）行分块 | 逐块抽出接口项目，返回 Tool Call `extract_interface_info.interfaces[]` |

- 两阶段都走 **Tool Calling**（`toolConfig.toolChoice = {"any": {}}`），强制模型以结构化工具入参返回。
- **提示词模板**：`prompts.yaml` 的 `phase1.template` / `phase2.template`，用 `str.format` 注入变量；文件缺失或展开失败时回退到 `ai_analyzer.py` 内置提示词（已记 warning）。

### 7.4 SAP AI Core 请求构造（`analyzer/sap_client.py`）

**Converse API**：`POST {base_url}/inference/deployments/{deployment_id}/converse`

```python
headers = {
  "Authorization": f"Bearer {token}",
  "AI-Resource-Group": resource_group,   # 默认 "default"
  "Content-Type": "application/json",
}
payload = {
  "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
  "inferenceConfig": {"maxTokens": 16384, "temperature": 0.7},
  "toolConfig": {"tools": tools, "toolChoice": {"any": {}}},   # 仅带 tools 时
}
```

- **模型不在前端选择**：由 deployment（`deployment_id`）决定，故无 `model` 字段、设置里也不暴露模型选择。

### 7.5 鉴权

`SAPAICoreClient._get_access_token`：`POST {auth_url}/oauth/token`，HTTP Basic（`client_id`/`client_secret`）+ `grant_type=client_credentials`；token 缓存在实例内复用；每请求带 `Authorization: Bearer`。凭证来自设置（`.env` 的 `AICORE_*`）。

---

## 8. Excel 格式

### 8.1 输入

| 项 | 要求 |
|---|---|
| 扩展名 | `.xlsx` / `.xls` / `.xlsm` |
| 输入 | 含接口设计书的文件夹（GUI **递归**扫描，含子目录） |
| 删除标记 | 删除线 / 对角划叉 / 富文本部分删除 自动跳过（`reader` 检测，`cleaner` 置空） |

### 8.2 输出产物（2 类）

| # | 产物 | 文件 | 复用代码 |
|---|---|---|---|
| ① | 抽出結果 Excel | `output/extracted/EBS定義書_抽出結果_<ts>.xlsx`（**汇总 1 个**，8 列） | `writer.py` |
| ② | 新フォーマット Excel | `output/formatted/IF抽出_<源文件名 stem>.xlsx`（**每文件 1 个**） | `formatter.py` |

- ① 列：`No., 文書管理番号, IF名, EBSテーブル名, EBSテーブルID, 項目ID, 項目名, 桁数`；空白单元格以 `-` 填充；文件名带时间戳防覆盖。
- ② 由 `reference/IF抽出_新フォーマット.xlsx` 模板 `shutil.copy2` 复制后写入：
  - **表紙**：`C21`=IF名、`H23`=日期；**改訂履歴**：`G2`=日期。
  - **対象IF**：用 `本社EBS現行IF一覧.xlsx` 按文件名/文书号模糊匹配出 FROM/TO 系统填入（值含 `EBS` 自动替换为 `SAP`）。
  - **IFマッピング定義**：AI 抽出记录从 Row5 起写入；超模板末行时复制 Row5 样式。

### 8.3 输出目录布局

```
output/
├── extracted/EBS定義書_抽出結果_<ts>.xlsx   ← 抽出結果汇总（①）
├── formatted/IF抽出_<源文件名>.xlsx          ← 新フォーマット（②，每文件 1 个）
├── logs/analyze_<ts>.log                     ← GUI 每次执行落盘的完整日志
└── analyzer_gui.log                          ← GUI 全局日志（logger 文件输出）
```
> `analyzer/logger.py` 另在 `output_dir` 下写 `analyzer.log`（核心层日语日志），日志查看器一并列出。

### 8.4 参考主数据（随分发，2 个）

| 文件 | 用途 | 依赖产物 |
|---|---|---|
| `reference/IF抽出_新フォーマット.xlsx` | 新フォーマット 模板 | ② |
| `reference/本社EBS現行IF一覧.xlsx` | 文档号 ↔ 送受信系统 主数据（sheet `現行IF一覧(EBS連携)`，K/L/M 列） | ② |

---

## 9. 配置与持久化

- **加载**：`Settings.load()` 用 `load_dotenv(_ENV_PATH, override=True)`，`_ENV_PATH = <仓库根>/.env`（基于 `settings.py` 文件位置 `parents[2]`，**与当前工作目录无关**）。`override=True` 让 `.env` 成为权威来源，覆盖残留系统环境变量。
- **GUI ↔ 核心配置桥接**：`core/config_factory.build_config(settings)` 把 GUI `Settings` 映射成 `analyzer.config.AppConfig`，使设置弹窗的修改即时生效（不再走 `analyzer.config.load_config()` 的环境变量路径）。
- **写回**：`Settings.save()` 用 `dotenv.set_key` 把全部字段写回**同一个** `_ENV_PATH`，逐键更新、保留其它内容。设置弹窗保存即调用，重启保留。
- **优先级**：`.env` 文件 > 系统环境变量 > 代码默认。
- **`.env` 键**：`INPUT_DIR / OUTPUT_DIR / TEMPLATE_PATH / REFERENCE_PATH / PHASE1_HEAD_ROWS / MAX_CHUNK_ROWS / AICORE_AUTH_URL / AICORE_CLIENT_ID / AICORE_CLIENT_SECRET / AICORE_BASE_URL / AICORE_RESOURCE_GROUP / AICORE_DEPLOYMENT_ID / LOG_LEVEL`。
- **日志**：`utils/logger.py` 初始化 root logger `analyzer_gui`，控制台 + `output/analyzer_gui.log` 双输出；重复调用安全（先清旧 handler）。

---

## 10. 多语言（i18n）

- **存储**：`i18n/locales/{zh,ja,en}.json`，key→文本，三语 key 一致（约 65 个 key）。
- **API**：`Translator` 单例 + 模块级 `t(key, **kwargs)`（支持 `str.format` 插值）；缺 key 回退默认语言（zh）再回退 key 本身；locale 文件按需读取并缓存。
- **持久化**：选中语言写到 `~/.ifmerge/config.json`，启动时读取，默认中文（zh）。
- **实时切换**：设置里选语言 → `SettingsDialog` 关闭并调 `app.set_language(code)` → 持久化 + 销毁/重建侧栏与页面（无需重启；会清空当前页已选文件与进度）。
- **覆盖范围**：界面文字、阶段文本（`phase.*`）、运行日志消息（`log.*`）、设置/日志查看器文案全部走 `t()`。
  > 注意：GUI 日志走 i18n（跟界面语言一致），**不**桥接 `analyzer/` 内部的日语 logger —— 后者仍以日语写入 `analyzer.log`。
