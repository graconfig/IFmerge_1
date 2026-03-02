"""Tests for ai_analyzer module: prompt builder and tool definition."""
import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from analyzer.ai_analyzer import (analyze_with_retry, build_phase1_prompt,
                                  build_phase1_tool, build_phase2_prompt,
                                  build_tool_definition)


class TestBuildPhase1Prompt:
    """Tests for build_phase1_prompt function."""

    def test_prompt_contains_sheet_text(self):
        result = build_phase1_prompt("=== Sheet: 表紙 ===", "f.xlsx")
        assert "表紙" in result

    def test_prompt_contains_file_name(self):
        result = build_phase1_prompt("data", "test.xlsx")
        assert "test.xlsx" in result

    def test_prompt_is_non_empty_string(self):
        result = build_phase1_prompt("data", "f.xlsx")
        assert isinstance(result, str) and len(result) > 0


class TestBuildPhase1Tool:
    """Tests for build_phase1_tool function."""

    def test_returns_list(self):
        assert isinstance(build_phase1_tool(), list)

    def test_tool_name(self):
        spec = build_phase1_tool()[0]['toolSpec']
        assert spec['name'] == 'extract_doc_meta'

    def test_schema_has_required_fields(self):
        schema = build_phase1_tool()[0]['toolSpec']['inputSchema']['json']
        assert 'document_number' in schema['properties']
        assert 'if_name' in schema['properties']
        assert 'data_sheets' in schema['properties']


class TestBuildPhase2Prompt:
    """Tests for build_phase2_prompt function."""

    def test_prompt_contains_chunk_text(self):
        result = build_phase2_prompt("DOC-001", "IF名", "data here", "f.xlsx")
        assert "data here" in result

    def test_prompt_contains_file_name(self):
        result = build_phase2_prompt("DOC-001", "IF名", "data", "test.xlsx")
        assert "test.xlsx" in result

    def test_prompt_contains_fixed_info(self):
        result = build_phase2_prompt("BDN-001", "出荷IF", "data", "f.xlsx")
        assert "BDN-001" in result
        assert "出荷IF" in result

    def test_prompt_with_japanese_content(self):
        result = build_phase2_prompt(
            "BDN-EPD-OF-093", "出荷指示情報",
            "テスト | データ", "test.xlsx",
        )
        assert "テスト" in result

    def test_prompt_with_empty_text(self):
        result = build_phase2_prompt("DOC", "IF", "", "f.xlsx")
        assert isinstance(result, str)


class TestBuildToolDefinition:
    """Tests for build_tool_definition function."""

    def test_returns_list(self):
        assert isinstance(build_tool_definition(), list)

    def test_returns_single_tool(self):
        assert len(build_tool_definition()) == 1

    def test_tool_name(self):
        spec = build_tool_definition()[0]['toolSpec']
        assert spec['name'] == 'extract_interface_info'

    def test_schema_matches_template_columns(self):
        spec = build_tool_definition()[0]['toolSpec']
        props = spec['inputSchema']['json']['properties']
        items_props = props['interfaces']['items']['properties']
        for field in ['document_number', 'if_name', 'ebs_table_name',
                      'ebs_table_id', 'item_id', 'item_name', 'digit_count']:
            assert field in items_props, f"Missing: {field}"

    def test_required_fields(self):
        items = build_tool_definition()[0]['toolSpec']['inputSchema']['json']['properties']['interfaces']['items']
        assert 'document_number' in items['required']
        assert 'if_name' in items['required']

    def test_schema_is_valid_json(self):
        result = build_tool_definition()
        serialized = json.dumps(result, ensure_ascii=False)
        assert json.loads(serialized) == result


class TestAnalyzeWithRetry:
    """Tests for analyze_with_retry function."""

    def _make_client(self, side_effect=None, return_value=None):
        client = MagicMock()
        if side_effect is not None:
            client.converse_with_tools.side_effect = side_effect
        elif return_value is not None:
            client.converse_with_tools.return_value = return_value
        return client

    def test_success_on_first_attempt(self):
        expected = {'extract_interface_info': {'interfaces': []}}
        client = self._make_client(return_value=expected)
        result = analyze_with_retry(client, "prompt", [{}])
        assert result == expected
        assert client.converse_with_tools.call_count == 1

    def test_success_after_one_failure(self):
        expected = {'extract_interface_info': {'interfaces': []}}
        client = self._make_client(side_effect=[
            Exception("API error"), expected,
        ])
        with patch('analyzer.ai_analyzer.time.sleep'):
            result = analyze_with_retry(client, "prompt", [{}])
        assert result == expected
        assert client.converse_with_tools.call_count == 2

    def test_raises_after_all_retries_exhausted(self):
        client = self._make_client(side_effect=[
            Exception("e1"), Exception("e2"), Exception("final"),
        ])
        with patch('analyzer.ai_analyzer.time.sleep'):
            with pytest.raises(Exception, match="final"):
                analyze_with_retry(client, "prompt", [{}])

    def test_passes_temperature_and_max_tokens(self):
        client = self._make_client(return_value={})
        tools = [{'toolSpec': {'name': 'test'}}]
        analyze_with_retry(client, "my prompt", tools)
        client.converse_with_tools.assert_called_once_with(
            "my prompt", tools, temperature=0.3, max_tokens=16384,
        )

    def test_custom_max_retries(self):
        client = self._make_client(side_effect=[
            Exception("e1"), Exception("e2"),
        ])
        with patch('analyzer.ai_analyzer.time.sleep'):
            with pytest.raises(Exception, match="e2"):
                analyze_with_retry(client, "prompt", [{}], max_retries=2)
        assert client.converse_with_tools.call_count == 2
