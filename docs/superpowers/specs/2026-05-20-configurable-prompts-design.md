# Configurable Prompts Design

## Overview

Make the AI prompts used by the SAP Interface document analyzer configurable via a YAML file, without breaking existing behavior if the file is absent.

## Problem

Phase 1 and Phase 2 prompt texts are hardcoded in `analyzer/ai_analyzer.py`. Tuning prompt behavior requires modifying source code.

## Approach: Approach A (Minimal)

No changes to `config.py` or `main.py`. Only `ai_analyzer.py` is modified (plus a new `prompts.yaml` file).

## Files Changed

### New: `prompts.yaml` (project root)

Structure:
```yaml
phase1:
  template: |
    <Phase 1 prompt text with {file_name} and {sheet_head_text} as placeholders>

phase2:
  template: |
    <Phase 2 prompt text with {file_name}, {doc_number}, {if_name}, {chunk_text} as placeholders>
```

- Initial content mirrors the current hardcoded prompts exactly.
- Users edit this file to tune prompt behavior — no code changes required.
- Template variables use Python `str.format()` style: `{variable_name}`.

### Modified: `analyzer/ai_analyzer.py`

**New constant:**
```python
_PROMPTS_FILE = Path('prompts.yaml')
```

**New module-level cache + loader:**
```python
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
        logger.warning("prompts.yaml not found, using built-in prompts")
        _templates_cache = {}
    except Exception as e:
        logger.warning("Failed to load prompts.yaml: %s, using built-in prompts", e)
        _templates_cache = {}
    return _templates_cache
```

**Modified `build_phase1_prompt`:**
- Check `_load_prompt_templates().get('phase1', {}).get('template')`
- If found: return `template.format(file_name=file_name, sheet_head_text=sheet_head_text)`
- If not: use existing f-string (fallback)

**Modified `build_phase2_prompt`:**
- Check `_load_prompt_templates().get('phase2', {}).get('template')`
- If found: return `template.format(file_name=file_name, doc_number=doc_number, if_name=if_name, chunk_text=chunk_text)`
- If not: use existing f-string (fallback)

## Template Variables

| Function | Variable | Description |
|---|---|---|
| Phase 1 | `{file_name}` | Excel filename |
| Phase 1 | `{sheet_head_text}` | Pre-formatted sheet preview text |
| Phase 2 | `{file_name}` | Excel filename |
| Phase 2 | `{doc_number}` | Document management number |
| Phase 2 | `{if_name}` | Interface name |
| Phase 2 | `{chunk_text}` | Pre-formatted data rows chunk |

Note: `col_table_name`, `col_table_id`, `col_item_id`, `col_digit` remain internal parameters — they are used for data filtering only, not inserted into the prompt text.

## Fallback Behavior

| Scenario | Result |
|---|---|
| `prompts.yaml` not found | Log warning, use built-in prompts |
| YAML parse error | Log warning, use built-in prompts |
| Key `phase1` or `phase2` missing | Use built-in prompt for that phase |
| `template` key missing under phase | Use built-in prompt for that phase |
| Template contains unknown `{variable}` | `str.format()` raises `KeyError` — log warning, use built-in prompt |

## Dependencies

`PyYAML` is required. Verify it is in `requirements.txt` (likely already present via openpyxl's dependency chain; add explicitly if missing).

## Non-Goals

- No UI for editing prompts
- No hot-reload of prompts during a single run (cached once per process)
- No per-file or per-sheet prompt customization
- No changes to `config.py` or `main.py`
