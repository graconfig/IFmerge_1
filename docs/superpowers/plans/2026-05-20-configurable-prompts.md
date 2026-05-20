# Configurable Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Phase 1 and Phase 2 AI prompt text editable via `prompts.yaml` at the project root, with automatic fallback to built-in prompts if the file is absent or malformed.

**Architecture:** A module-level `_load_prompt_templates()` function in `ai_analyzer.py` reads and caches `prompts.yaml` on first call. `build_phase1_prompt` and `build_phase2_prompt` call this function and use `str.format()` on the loaded template, falling back to the existing f-string on any failure.

**Tech Stack:** Python 3.11+, PyYAML 6.x, pytest

---

## File Map

| Action | Path | Change |
|---|---|---|
| Modify | `requirements.txt` | Add `PyYAML>=6.0` |
| Modify | `analyzer/test_ai_analyzer.py` | Add tests for YAML loading and fallback |
| Modify | `analyzer/ai_analyzer.py` | Add loader + modify build functions |
| Create | `prompts.yaml` | Phase 1 and Phase 2 template text |

---

### Task 1: Add PyYAML dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add PyYAML to requirements.txt**

Open `requirements.txt` and add the line `PyYAML>=6.0` after the existing entries:

```
openpyxl>=3.1.0
requests>=2.31.0
python-dotenv>=1.0
pytest>=7.0
hypothesis>=6.0
xlrd>=1.2.0
pywin32
PyYAML>=6.0
```

- [ ] **Step 2: Install**

```bash
pip install PyYAML>=6.0
```

Expected: `Successfully installed PyYAML-...` (or already satisfied)

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add PyYAML dependency for configurable prompts"
```

---

### Task 2: Write failing tests for YAML loading behavior

**Files:**
- Modify: `analyzer/test_ai_analyzer.py`

- [ ] **Step 1: Add the new test classes to `analyzer/test_ai_analyzer.py`**

Append the following to the end of the existing file (after the `TestAnalyzeWithRetry` class):

```python
# ---------------------------------------------------------------------------
# Tests for YAML-based prompt loading
# ---------------------------------------------------------------------------
import analyzer.ai_analyzer as ai_module
from pathlib import Path


@pytest.fixture(autouse=False)
def reset_prompt_cache():
    """Reset the module-level template cache before and after each test."""
    ai_module._templates_cache = None
    yield
    ai_module._templates_cache = None


class TestLoadPromptTemplates:
    """Tests for _load_prompt_templates function."""

    def test_returns_empty_dict_when_file_missing(self, reset_prompt_cache, tmp_path):
        with patch.object(ai_module, '_PROMPTS_FILE', tmp_path / 'nonexistent.yaml'):
            result = ai_module._load_prompt_templates()
        assert result == {}

    def test_returns_templates_when_file_exists(self, reset_prompt_cache, tmp_path):
        yaml_file = tmp_path / 'prompts.yaml'
        yaml_file.write_text(
            'phase1:\n  template: "hello {file_name}"\n', encoding='utf-8'
        )
        with patch.object(ai_module, '_PROMPTS_FILE', yaml_file):
            result = ai_module._load_prompt_templates()
        assert result['phase1']['template'] == 'hello {file_name}'

    def test_returns_empty_dict_on_invalid_yaml(self, reset_prompt_cache, tmp_path):
        yaml_file = tmp_path / 'prompts.yaml'
        yaml_file.write_text('invalid: [yaml:\n  unclosed', encoding='utf-8')
        with patch.object(ai_module, '_PROMPTS_FILE', yaml_file):
            result = ai_module._load_prompt_templates()
        assert result == {}

    def test_caches_result_on_second_call(self, reset_prompt_cache, tmp_path):
        yaml_file = tmp_path / 'prompts.yaml'
        yaml_file.write_text('phase1:\n  template: "t"\n', encoding='utf-8')
        with patch.object(ai_module, '_PROMPTS_FILE', yaml_file):
            r1 = ai_module._load_prompt_templates()
            r2 = ai_module._load_prompt_templates()
        assert r1 is r2


class TestBuildPhase1PromptWithYaml:
    """Tests for build_phase1_prompt using YAML template."""

    def test_uses_yaml_template_when_available(self):
        tpls = {'phase1': {'template': 'Custom: {file_name} data: {sheet_head_text}'}}
        with patch.object(ai_module, '_load_prompt_templates', return_value=tpls):
            result = build_phase1_prompt('rows', 'file.xlsx')
        assert result == 'Custom: file.xlsx data: rows'

    def test_falls_back_to_builtin_when_yaml_missing(self):
        with patch.object(ai_module, '_load_prompt_templates', return_value={}):
            result = build_phase1_prompt('rows', 'file.xlsx')
        assert 'file.xlsx' in result
        assert 'rows' in result

    def test_falls_back_when_template_has_unknown_variable(self):
        tpls = {'phase1': {'template': 'Hello {unknown_var}'}}
        with patch.object(ai_module, '_load_prompt_templates', return_value=tpls):
            result = build_phase1_prompt('rows', 'file.xlsx')
        assert 'file.xlsx' in result
        assert 'rows' in result


class TestBuildPhase2PromptWithYaml:
    """Tests for build_phase2_prompt using YAML template."""

    def test_uses_yaml_template_when_available(self):
        tpls = {'phase2': {'template': '{doc_number}|{if_name}|{chunk_text}|{file_name}'}}
        with patch.object(ai_module, '_load_prompt_templates', return_value=tpls):
            result = build_phase2_prompt('D001', 'IF1', 'rows', 'f.xlsx')
        assert result == 'D001|IF1|rows|f.xlsx'

    def test_falls_back_to_builtin_when_yaml_missing(self):
        with patch.object(ai_module, '_load_prompt_templates', return_value={}):
            result = build_phase2_prompt('D001', 'IF1', 'rows', 'f.xlsx')
        assert 'D001' in result
        assert 'IF1' in result

    def test_falls_back_when_template_has_unknown_variable(self):
        tpls = {'phase2': {'template': 'Bad {unknown}'}}
        with patch.object(ai_module, '_load_prompt_templates', return_value=tpls):
            result = build_phase2_prompt('D001', 'IF1', 'rows', 'f.xlsx')
        assert 'D001' in result
        assert 'IF1' in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest analyzer/test_ai_analyzer.py::TestLoadPromptTemplates analyzer/test_ai_analyzer.py::TestBuildPhase1PromptWithYaml analyzer/test_ai_analyzer.py::TestBuildPhase2PromptWithYaml -v
```

Expected: All new tests FAIL with `AttributeError: module 'analyzer.ai_analyzer' has no attribute '_templates_cache'` (or similar).

- [ ] **Step 3: Commit failing tests**

```bash
git add analyzer/test_ai_analyzer.py
git commit -m "test: add failing tests for YAML prompt loading"
```

---

### Task 3: Implement YAML loader and modify build functions

**Files:**
- Modify: `analyzer/ai_analyzer.py:1-41` and `analyzer/ai_analyzer.py:107-153`

- [ ] **Step 1: Add Path import and module-level constants after the existing imports in `ai_analyzer.py`**

The current imports section at the top of `analyzer/ai_analyzer.py` ends at line 13. Add `Path` to the existing stdlib imports and add two new module-level declarations.

Replace:
```python
import logging
import time

from analyzer.sap_client import SAPAICoreClient

logger = logging.getLogger('analyzer')

# デフォルト値（AppConfig から上書き可能）
_DEFAULT_PHASE1_HEAD_ROWS = 30
_DEFAULT_MAX_CHUNK_ROWS = 100
```

With:
```python
import logging
import time
from pathlib import Path

from analyzer.sap_client import SAPAICoreClient

logger = logging.getLogger('analyzer')

# デフォルト値（AppConfig から上書き可能）
_DEFAULT_PHASE1_HEAD_ROWS = 30
_DEFAULT_MAX_CHUNK_ROWS = 100

_PROMPTS_FILE = Path('prompts.yaml')
_templates_cache: dict | None = None


def _load_prompt_templates() -> dict:
    """Load prompts.yaml once and cache. Returns {} on any failure."""
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache
    try:
        import yaml
        with open(_PROMPTS_FILE, encoding='utf-8') as f:
            _templates_cache = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning("prompts.yaml が見つかりません。内蔵プロンプトを使用します。")
        _templates_cache = {}
    except Exception as e:
        logger.warning(
            "prompts.yaml の読み込みに失敗しました: %s — 内蔵プロンプトを使用します。", e,
        )
        _templates_cache = {}
    return _templates_cache
```

- [ ] **Step 2: Modify `build_phase1_prompt` to use YAML template**

Replace the entire `build_phase1_prompt` function (lines 21–41):

```python
def build_phase1_prompt(sheet_head_text: str, file_name: str) -> str:
    """Phase 1: 全シートの先頭部分から固定情報・データシート・列構造を識別する。"""
    tmpl = _load_prompt_templates().get('phase1', {}).get('template')
    if tmpl:
        try:
            return tmpl.format(file_name=file_name, sheet_head_text=sheet_head_text)
        except (KeyError, ValueError) as e:
            logger.warning(
                "phase1テンプレートの展開に失敗しました: %s — 内蔵プロンプトを使用します。", e,
            )
    return f"""以下はSAP Interface設計書（{file_name}）の各シートの先頭部分です。
各行の各セルは [列番号]値 の形式で表示されています。

{sheet_head_text}

以下を識別してください：
1. document_number: 文書管理番号（例: BDN-EPD-OF-093）
2. if_name: インターフェース名称
3. data_sheets: EBSテーブルの項目一覧が記載されているシートのみ
   （「エクスポート項目」「インポート項目」「データ項目」等。
    「表紙」「処理概要」「変更履歴」「テーブル一覧」等は除外すること）
4. 各データシートについて：
   - data_start_row: データ行（項目一覧）が始まる行番号（0始まり）
   - col_table_name: EBSテーブル名（日本語）が入っている列番号（不明な場合は-1）
   - col_table_id: EBSテーブルID（英語）が入っている列番号
   - col_item_id: 項目ID（英語カラム名）が入っている列番号
   - col_digit: 桁数（バイト長）が入っている列番号（不明な場合は-1）

extract_doc_metaツールを使って結果を返してください。"""
```

- [ ] **Step 3: Modify `build_phase2_prompt` to use YAML template**

Replace the entire `build_phase2_prompt` function (lines 107–153):

```python
def build_phase2_prompt(doc_number: str, if_name: str,
                        chunk_text: str, file_name: str,
                        col_table_name: int = -1, col_table_id: int = -1,
                        col_item_id: int = -1, col_digit: int = -1) -> str:
    """Phase 2: 固定情報をコンテキストとして、データ行チャンクから項目を抽出する。"""
    tmpl = _load_prompt_templates().get('phase2', {}).get('template')
    if tmpl:
        try:
            return tmpl.format(
                file_name=file_name, doc_number=doc_number,
                if_name=if_name, chunk_text=chunk_text,
            )
        except (KeyError, ValueError) as e:
            logger.warning(
                "phase2テンプレートの展開に失敗しました: %s — 内蔵プロンプトを使用します。", e,
            )
    return f"""以下はSAP Interface設計書（{file_name}）のデータ行の一部です。
各セルは [列番号]値 の形式で表示されています。

固定情報（全行共通）：
- 文書管理番号: {doc_number}
- IF名: {if_name}

データ行：
{chunk_text}

上記のデータ行から、各項目を抽出してください。抽出できない情報は空でよい：
1. ebs_table_name: EBSテーブルの日本語名称
2. ebs_table_id: EBSテーブルの英語ID
3. item_id: 各項目の英語ID/カラム名
4. item_name: 各項目の日本語名称
5. digit_count: 各項目の桁数
6. item_description: 項目の詳細説明（備考欄や説明欄から取得）
7. data_type: データ型（VARCHAR2, NUMBER, DATE等）
8. digit_decimal: 桁数（小数点以下）
9. dev_type: 標準/追加開発
10. is_key: キー項目（●など）
11. required: 必須/任意
12. remarks: 備考

重要なルール：
- 一セルに複数行の項目が記載されている場合は、それぞれ分割して出力すること。
- 項目ID（英語カラム名）を1つずつ漏れなく抽出すること。
- 同じNo（番号）に複数の項目IDが属している場合（No列が空白で続く行）は、1行にまとめること：
  * 項目ID: カンマ区切りで連結
  * 項目名: カンマ区切りで連結
  * 桁数: カンマ区切りで連結
- EBSテーブル名/IDはデータ行から読み取ること。途中で変わる場合は変わった後の値を使用。
- IF項目のみを出力すること。処理概要などの説明行は出力しないこと。
- 文書管理番号とIF名は上記の固定情報をそのまま使用すること。
- セル内のノイズ除去ルール：
  * 【履歴管理】およびそれ以降の文字列（番号・記号・丸数字含む）はすべて除去すること（例: 「契約情報　【履歴管理】④」→「契約情報」）
  * [Vx.xx]形式のバージョン番号は除去すること（例: 「TAX代替ビュー(ID)  [V1.09]」→「TAX代替ビュー(ID)」）
  * セルに「×」「＊」「*」などの演算記号が含まれる場合、その記号より前の英語ID部分のみを使用すること（例: 「TAX_RATE  ×  0.01」→「TAX_RATE」）
  * 項目IDセルの値が演算記号のみ、または演算記号で始まる場合（英語IDが含まれない場合）はその行をスキップすること

extract_interface_infoツールを使って結果を返してください。"""
```

- [ ] **Step 4: Run all new tests to verify they pass**

```bash
pytest analyzer/test_ai_analyzer.py::TestLoadPromptTemplates analyzer/test_ai_analyzer.py::TestBuildPhase1PromptWithYaml analyzer/test_ai_analyzer.py::TestBuildPhase2PromptWithYaml -v
```

Expected: All 10 new tests PASS.

- [ ] **Step 5: Run the full test suite to confirm nothing is broken**

```bash
pytest analyzer/ -v
```

Expected: All tests PASS (existing tests still pass via built-in fallback since `prompts.yaml` doesn't exist yet).

- [ ] **Step 6: Commit**

```bash
git add analyzer/ai_analyzer.py
git commit -m "feat: add YAML prompt loader with built-in fallback"
```

---

### Task 4: Create `prompts.yaml` with current prompt content

**Files:**
- Create: `prompts.yaml`

- [ ] **Step 1: Create `prompts.yaml` at project root**

Create the file with the following content (this mirrors the built-in prompts exactly):

```yaml
# SAP Interface設計書 分析プロンプト設定
# 変数プレースホルダ：{file_name}, {sheet_head_text} (phase1) / {doc_number}, {if_name}, {chunk_text} (phase2)

phase1:
  template: |
    以下はSAP Interface設計書（{file_name}）の各シートの先頭部分です。
    各行の各セルは [列番号]値 の形式で表示されています。

    {sheet_head_text}

    以下を識別してください：
    1. document_number: 文書管理番号（例: BDN-EPD-OF-093）
    2. if_name: インターフェース名称
    3. data_sheets: EBSテーブルの項目一覧が記載されているシートのみ
       （「エクスポート項目」「インポート項目」「データ項目」等。
        「表紙」「処理概要」「変更履歴」「テーブル一覧」等は除外すること）
    4. 各データシートについて：
       - data_start_row: データ行（項目一覧）が始まる行番号（0始まり）
       - col_table_name: EBSテーブル名（日本語）が入っている列番号（不明な場合は-1）
       - col_table_id: EBSテーブルID（英語）が入っている列番号
       - col_item_id: 項目ID（英語カラム名）が入っている列番号
       - col_digit: 桁数（バイト長）が入っている列番号（不明な場合は-1）

    extract_doc_metaツールを使って結果を返してください。

phase2:
  template: |
    以下はSAP Interface設計書（{file_name}）のデータ行の一部です。
    各セルは [列番号]値 の形式で表示されています。

    固定情報（全行共通）：
    - 文書管理番号: {doc_number}
    - IF名: {if_name}

    データ行：
    {chunk_text}

    上記のデータ行から、各項目を抽出してください。抽出できない情報は空でよい：
    1. ebs_table_name: EBSテーブルの日本語名称
    2. ebs_table_id: EBSテーブルの英語ID
    3. item_id: 各項目の英語ID/カラム名
    4. item_name: 各項目の日本語名称
    5. digit_count: 各項目の桁数
    6. item_description: 項目の詳細説明（備考欄や説明欄から取得）
    7. data_type: データ型（VARCHAR2, NUMBER, DATE等）
    8. digit_decimal: 桁数（小数点以下）
    9. dev_type: 標準/追加開発
    10. is_key: キー項目（●など）
    11. required: 必須/任意
    12. remarks: 備考

    重要なルール：
    - 一セルに複数行の項目が記載されている場合は、それぞれ分割して出力すること。
    - 項目ID（英語カラム名）を1つずつ漏れなく抽出すること。
    - 同じNo（番号）に複数の項目IDが属している場合（No列が空白で続く行）は、1行にまとめること：
      * 項目ID: カンマ区切りで連結
      * 項目名: カンマ区切りで連結
      * 桁数: カンマ区切りで連結
    - EBSテーブル名/IDはデータ行から読み取ること。途中で変わる場合は変わった後の値を使用。
    - IF項目のみを出力すること。処理概要などの説明行は出力しないこと。
    - 文書管理番号とIF名は上記の固定情報をそのまま使用すること。
    - セル内のノイズ除去ルール：
      * 【履歴管理】およびそれ以降の文字列（番号・記号・丸数字含む）はすべて除去すること（例: 「契約情報　【履歴管理】④」→「契約情報」）
      * [Vx.xx]形式のバージョン番号は除去すること（例: 「TAX代替ビュー(ID)  [V1.09]」→「TAX代替ビュー(ID)」）
      * セルに「×」「＊」「*」などの演算記号が含まれる場合、その記号より前の英語ID部分のみを使用すること（例: 「TAX_RATE  ×  0.01」→「TAX_RATE」）
      * 項目IDセルの値が演算記号のみ、または演算記号で始まる場合（英語IDが含まれない場合）はその行をスキップすること

    extract_interface_infoツールを使って結果を返してください。
```

- [ ] **Step 2: Verify the full test suite still passes**

```bash
pytest analyzer/ -v
```

Expected: All tests PASS. (The existing content-check tests pass because YAML templates contain the same text as the built-in prompts.)

- [ ] **Step 3: Commit**

```bash
git add prompts.yaml
git commit -m "feat: add prompts.yaml with configurable Phase 1 and Phase 2 templates"
```
