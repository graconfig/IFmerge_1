import logging

import pytest

from analyzer.cleaner import CleanedSheet, clean_sheet_data, format_as_text
from analyzer.reader import CellData, SheetData


def _cell(value: str | None, strike: bool = False) -> CellData:
    """Helper to create a CellData instance."""
    return CellData(value=value, is_strikethrough=strike)


def _sheet(name: str, rows: list[list[CellData]]) -> SheetData:
    """Helper to create a SheetData instance."""
    return SheetData(name=name, rows=rows)


class TestCleanSheetData:
    """Tests for clean_sheet_data function."""

    def test_basic_cleaning(self):
        """clean_sheet_data should return cleaned data with headers and rows."""
        sheet = _sheet("Sheet1", [
            [_cell("Header1"), _cell("Header2")],
            [_cell("A"), _cell("B")],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.name == "Sheet1"
        assert result.headers == ["Header1", "Header2"]
        assert result.rows == [["A", "B"]]

    def test_removes_all_empty_rows(self):
        """clean_sheet_data should remove rows where all cells are empty (Req 2.1)."""
        sheet = _sheet("Sheet1", [
            [_cell("Header")],
            [_cell(None)],
            [_cell("")],
            [_cell("Data")],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.headers == ["Header"]
        assert result.rows == [["Data"]]

    def test_removes_whitespace_only_rows(self):
        """clean_sheet_data should remove rows with only whitespace (Req 2.1)."""
        sheet = _sheet("Sheet1", [
            [_cell("Header")],
            [_cell("   "), _cell("  \t  ")],
            [_cell("Data")],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.headers == ["Header"]
        assert result.rows == [["Data"]]

    def test_excludes_strikethrough_text(self):
        """clean_sheet_data should replace strikethrough text with empty string (Req 2.2)."""
        sheet = _sheet("Sheet1", [
            [_cell("Header"), _cell("StrikeHeader", strike=True)],
            [_cell("Normal"), _cell("Deleted", strike=True)],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.headers == ["Header", ""]
        assert result.rows == [["Normal", ""]]

    def test_preserves_original_text_content(self):
        """clean_sheet_data should preserve text content, stripping whitespace (Req 2.3)."""
        sheet = _sheet("Sheet1", [
            [_cell("  Header  ")],
            [_cell("  Data Value  ")],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.headers == ["Header"]
        assert result.rows == [["Data Value"]]

    def test_returns_none_for_all_empty_sheet(self):
        """clean_sheet_data should return None when all rows are empty (Req 2.5)."""
        sheet = _sheet("EmptySheet", [
            [_cell(None), _cell("")],
            [_cell(""), _cell(None)],
        ])
        result = clean_sheet_data(sheet)
        assert result is None

    def test_returns_none_for_sheet_with_no_rows(self):
        """clean_sheet_data should return None for a sheet with no rows."""
        sheet = _sheet("NoRows", [])
        result = clean_sheet_data(sheet)
        assert result is None

    def test_logs_message_for_empty_sheet(self, caplog):
        """clean_sheet_data should log a message when sheet is empty after cleaning (Req 2.5)."""
        sheet = _sheet("EmptySheet", [
            [_cell(None)],
        ])
        with caplog.at_level(logging.INFO, logger="analyzer"):
            result = clean_sheet_data(sheet)
        assert result is None
        assert "EmptySheet" in caplog.text

    def test_only_header_row(self):
        """clean_sheet_data should handle sheet with only a header row (no data rows)."""
        sheet = _sheet("HeaderOnly", [
            [_cell("Col1"), _cell("Col2")],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.headers == ["Col1", "Col2"]
        assert result.rows == []

    def test_strikethrough_only_row_is_removed(self):
        """A row with only strikethrough cells should be treated as empty and removed."""
        sheet = _sheet("Sheet1", [
            [_cell("Header")],
            [_cell("Deleted1", strike=True), _cell("Deleted2", strike=True)],
            [_cell("Kept")],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.headers == ["Header"]
        assert result.rows == [["Kept"]]

    def test_mixed_strikethrough_and_normal(self):
        """Rows with mix of strikethrough and normal cells should be kept."""
        sheet = _sheet("Sheet1", [
            [_cell("H1"), _cell("H2")],
            [_cell("Normal"), _cell("Strike", strike=True)],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.rows == [["Normal", ""]]

    def test_returns_cleaned_sheet_type(self):
        """clean_sheet_data should return a CleanedSheet instance."""
        sheet = _sheet("Sheet1", [
            [_cell("Data")],
        ])
        result = clean_sheet_data(sheet)
        assert isinstance(result, CleanedSheet)

    def test_none_value_becomes_empty_string(self):
        """None cell values should become empty strings in cleaned output."""
        sheet = _sheet("Sheet1", [
            [_cell("Header"), _cell(None)],
            [_cell(None), _cell("Value")],
        ])
        result = clean_sheet_data(sheet)
        assert result is not None
        assert result.headers == ["Header", ""]
        assert result.rows == [["", "Value"]]


class TestFormatAsText:
    """Tests for format_as_text function."""

    def test_basic_formatting(self):
        """format_as_text should produce structured text output (Req 2.4)."""
        sheets = [CleanedSheet(
            name="Sheet1",
            headers=["Col1", "Col2"],
            rows=[["A", "B"], ["C", "D"]],
        )]
        result = format_as_text(sheets)
        assert "=== Sheet: Sheet1 ===" in result
        assert "Col1 | Col2" in result
        assert "-" * 40 in result
        assert "A | B" in result
        assert "C | D" in result

    def test_multiple_sheets(self):
        """format_as_text should format multiple sheets."""
        sheets = [
            CleanedSheet(name="First", headers=["H1"], rows=[["R1"]]),
            CleanedSheet(name="Second", headers=["H2"], rows=[["R2"]]),
        ]
        result = format_as_text(sheets)
        assert "=== Sheet: First ===" in result
        assert "=== Sheet: Second ===" in result
        assert "H1" in result
        assert "H2" in result

    def test_empty_list_returns_empty_string(self):
        """format_as_text should return empty string for empty list."""
        result = format_as_text([])
        assert result == ""

    def test_sheet_with_no_headers(self):
        """format_as_text should handle sheet with empty headers."""
        sheets = [CleanedSheet(name="NoHeaders", headers=[], rows=[["A", "B"]])]
        result = format_as_text(sheets)
        assert "=== Sheet: NoHeaders ===" in result
        assert "A | B" in result
        # No separator line when no headers
        assert "-" * 40 not in result

    def test_sheet_with_headers_only(self):
        """format_as_text should handle sheet with headers but no data rows."""
        sheets = [CleanedSheet(name="HeadersOnly", headers=["H1", "H2"], rows=[])]
        result = format_as_text(sheets)
        assert "=== Sheet: HeadersOnly ===" in result
        assert "H1 | H2" in result
        assert "-" * 40 in result

    def test_japanese_sheet_names(self):
        """format_as_text should handle Japanese sheet names correctly."""
        sheets = [CleanedSheet(
            name="インターフェース一覧",
            headers=["項目"],
            rows=[["値"]],
        )]
        result = format_as_text(sheets)
        assert "=== Sheet: インターフェース一覧 ===" in result

    def test_output_line_order(self):
        """format_as_text should output lines in correct order."""
        sheets = [CleanedSheet(
            name="Test",
            headers=["H1"],
            rows=[["R1"], ["R2"]],
        )]
        result = format_as_text(sheets)
        lines = result.split("\n")
        assert lines[0] == "=== Sheet: Test ==="
        assert lines[1] == "H1"
        assert lines[2] == "-" * 40
        assert lines[3] == "R1"
        assert lines[4] == "R2"
