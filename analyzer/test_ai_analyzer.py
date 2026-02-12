"""Tests for ai_analyzer module: prompt builder and tool definition."""
import pytest

from analyzer.ai_analyzer import build_analysis_prompt, build_tool_definition


class TestBuildAnalysisPrompt:
    """Tests for build_analysis_prompt function."""

    def test_prompt_contains_cleaned_text(self):
        """Prompt must contain the full cleaned text content."""
        cleaned_text = "=== Sheet: Data ===\ncol1 | col2\n--------\nval1 | val2"
        file_name = "test_file.xlsx"
        prompt = build_analysis_prompt(cleaned_text, file_name)
        assert cleaned_text in prompt

    def test_prompt_contains_file_name(self):
        """Prompt must contain the file name for context."""
        cleaned_text = "some data"
        file_name = "BDN-EPD-OF-093_設計書.xlsx"
        prompt = build_analysis_prompt(cleaned_text, file_name)
        assert file_name in prompt

    def test_prompt_is_non_empty_string(self):
        """Prompt must be a non-empty string."""
        prompt = build_analysis_prompt("data", "file.xlsx")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_with_multiline_text(self):
        """Prompt preserves multiline cleaned text."""
        cleaned_text = "line1\nline2\nline3"
        prompt = build_analysis_prompt(cleaned_text, "test.xlsx")
        assert "line1\nline2\nline3" in prompt

    def test_prompt_with_japanese_content(self):
        """Prompt handles Japanese characters in both text and filename."""
        cleaned_text = "出荷指示データ | ホスト"
        file_name = "インターフェース設計書.xlsx"
        prompt = build_analysis_prompt(cleaned_text, file_name)
        assert cleaned_text in prompt
        assert file_name in prompt

    def test_prompt_with_empty_text(self):
        """Prompt still works with empty cleaned text."""
        prompt = build_analysis_prompt("", "file.xlsx")
        assert "file.xlsx" in prompt
        assert isinstance(prompt, str)


class TestBuildToolDefinition:
    """Tests for build_tool_definition function."""

    def test_returns_list(self):
        """Tool definition must be a list."""
        result = build_tool_definition()
        assert isinstance(result, list)

    def test_returns_single_tool(self):
        """Tool definition list must contain exactly one tool."""
        result = build_tool_definition()
        assert len(result) == 1

    def test_tool_has_toolspec_structure(self):
        """Tool must have the toolSpec wrapper structure."""
        tool = build_tool_definition()[0]
        assert 'toolSpec' in tool
        spec = tool['toolSpec']
        assert 'name' in spec
        assert 'description' in spec
        assert 'inputSchema' in spec

    def test_tool_name(self):
        """Tool name must be 'extract_interface_info'."""
        spec = build_tool_definition()[0]['toolSpec']
        assert spec['name'] == 'extract_interface_info'

    def test_input_schema_has_interfaces_array(self):
        """Schema must have an 'interfaces' array at the top level."""
        spec = build_tool_definition()[0]['toolSpec']
        schema = spec['inputSchema']['json']
        assert schema['type'] == 'object'
        assert 'interfaces' in schema['properties']
        assert schema['properties']['interfaces']['type'] == 'array'
        assert 'interfaces' in schema['required']

    def test_schema_matches_template_columns(self):
        """Schema item properties must match the output template columns.

        Output template columns (from ②_INPUT_EBS定義書の抽出結果.xlsx):
        No. | 文書管理番号 | IF名 | EBSテーブル名 | EBSテーブルID | 項目ID | 項目名 | 桁数

        No. is auto-generated, so the remaining 7 columns should be in the schema.
        """
        spec = build_tool_definition()[0]['toolSpec']
        item_props = spec['inputSchema']['json']['properties']['interfaces']['items']['properties']

        expected_fields = [
            'document_number',   # 文書管理番号
            'if_name',           # IF名
            'ebs_table_name',    # EBSテーブル名
            'ebs_table_id',      # EBSテーブルID
            'item_id',           # 項目ID
            'item_name',         # 項目名
            'digit_count',       # 桁数
        ]
        for field in expected_fields:
            assert field in item_props, f"Missing field: {field}"

    def test_required_fields(self):
        """Schema must require document_number and if_name."""
        spec = build_tool_definition()[0]['toolSpec']
        items = spec['inputSchema']['json']['properties']['interfaces']['items']
        assert 'required' in items
        assert 'document_number' in items['required']
        assert 'if_name' in items['required']

    def test_all_properties_have_type_string(self):
        """All item properties must have type 'string'."""
        spec = build_tool_definition()[0]['toolSpec']
        item_props = spec['inputSchema']['json']['properties']['interfaces']['items']['properties']
        for field_name, field_def in item_props.items():
            assert field_def['type'] == 'string', f"Field {field_name} should be type 'string'"

    def test_all_properties_have_description(self):
        """All item properties must have a description."""
        spec = build_tool_definition()[0]['toolSpec']
        item_props = spec['inputSchema']['json']['properties']['interfaces']['items']['properties']
        for field_name, field_def in item_props.items():
            assert 'description' in field_def, f"Field {field_name} missing description"
            assert len(field_def['description']) > 0, f"Field {field_name} has empty description"

    def test_schema_is_valid_json_structure(self):
        """The entire schema must be a valid nested dict structure (JSON-serializable)."""
        import json
        result = build_tool_definition()
        # Should not raise
        serialized = json.dumps(result, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized == result


from unittest.mock import MagicMock, patch
from analyzer.ai_analyzer import analyze_with_retry


class TestAnalyzeWithRetry:
    """Tests for analyze_with_retry function."""

    def _make_client(self, side_effect=None, return_value=None):
        """Helper to create a mock SAPAICoreClient."""
        client = MagicMock()
        if side_effect is not None:
            client.converse_with_tools.side_effect = side_effect
        elif return_value is not None:
            client.converse_with_tools.return_value = return_value
        return client

    def test_success_on_first_attempt(self):
        """Returns result immediately when first call succeeds."""
        expected = {'extract_interface_info': {'interfaces': []}}
        client = self._make_client(return_value=expected)

        result = analyze_with_retry(client, "prompt", [{}])

        assert result == expected
        assert client.converse_with_tools.call_count == 1

    def test_success_after_one_failure(self):
        """Retries and returns result after one transient failure."""
        expected = {'extract_interface_info': {'interfaces': []}}
        client = self._make_client(side_effect=[
            Exception("API error"),
            expected,
        ])

        with patch('analyzer.ai_analyzer.time.sleep') as mock_sleep:
            result = analyze_with_retry(client, "prompt", [{}])

        assert result == expected
        assert client.converse_with_tools.call_count == 2
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    def test_success_after_two_failures(self):
        """Retries twice and returns result on third attempt."""
        expected = {'extract_interface_info': {'interfaces': []}}
        client = self._make_client(side_effect=[
            Exception("error 1"),
            Exception("error 2"),
            expected,
        ])

        with patch('analyzer.ai_analyzer.time.sleep') as mock_sleep:
            result = analyze_with_retry(client, "prompt", [{}])

        assert result == expected
        assert client.converse_with_tools.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)   # 2^0 = 1
        mock_sleep.assert_any_call(2)   # 2^1 = 2

    def test_raises_after_all_retries_exhausted(self):
        """Raises the last exception after max_retries failures."""
        client = self._make_client(side_effect=[
            Exception("error 1"),
            Exception("error 2"),
            Exception("final error"),
        ])

        with patch('analyzer.ai_analyzer.time.sleep'):
            with pytest.raises(Exception, match="final error"):
                analyze_with_retry(client, "prompt", [{}])

        assert client.converse_with_tools.call_count == 3

    def test_exponential_backoff_timing(self):
        """Wait times follow exponential backoff: 2^0, 2^1, ..."""
        client = self._make_client(side_effect=[
            Exception("e1"),
            Exception("e2"),
            Exception("e3"),
        ])

        with patch('analyzer.ai_analyzer.time.sleep') as mock_sleep:
            with pytest.raises(Exception):
                analyze_with_retry(client, "prompt", [{}])

        # Only 2 sleeps (between attempts 1→2 and 2→3, not after last failure)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # 2^0
        mock_sleep.assert_any_call(2)  # 2^1

    def test_passes_temperature_0_3(self):
        """Calls converse_with_tools with temperature=0.3."""
        client = self._make_client(return_value={})
        tools = [{'toolSpec': {'name': 'test'}}]

        analyze_with_retry(client, "my prompt", tools)

        client.converse_with_tools.assert_called_once_with(
            "my prompt", tools, temperature=0.3, max_tokens=16384
        )

    def test_custom_max_retries(self):
        """Respects custom max_retries parameter."""
        client = self._make_client(side_effect=[
            Exception("e1"),
            Exception("e2"),
        ])

        with patch('analyzer.ai_analyzer.time.sleep'):
            with pytest.raises(Exception, match="e2"):
                analyze_with_retry(client, "prompt", [{}], max_retries=2)

        assert client.converse_with_tools.call_count == 2

    def test_max_retries_one_no_retry(self):
        """With max_retries=1, raises immediately without sleeping."""
        client = self._make_client(side_effect=Exception("immediate fail"))

        with patch('analyzer.ai_analyzer.time.sleep') as mock_sleep:
            with pytest.raises(Exception, match="immediate fail"):
                analyze_with_retry(client, "prompt", [{}], max_retries=1)

        mock_sleep.assert_not_called()

    def test_logs_retry_attempts(self, caplog):
        """Logs warning messages on retry attempts."""
        expected = {'result': 'ok'}
        client = self._make_client(side_effect=[
            Exception("transient error"),
            expected,
        ])

        with patch('analyzer.ai_analyzer.time.sleep'):
            import logging
            with caplog.at_level(logging.WARNING, logger='analyzer'):
                result = analyze_with_retry(client, "prompt", [{}])

        assert result == expected
        assert any("AI呼び出し失敗" in record.message for record in caplog.records)

    def test_logs_error_on_final_failure(self, caplog):
        """Logs error message when all retries are exhausted."""
        client = self._make_client(side_effect=[
            Exception("e1"),
            Exception("e2"),
            Exception("e3"),
        ])

        with patch('analyzer.ai_analyzer.time.sleep'):
            import logging
            with caplog.at_level(logging.ERROR, logger='analyzer'):
                with pytest.raises(Exception):
                    analyze_with_retry(client, "prompt", [{}])

        assert any("全リトライ失敗" in record.message for record in caplog.records)
