import os
from pathlib import Path

import pytest

from analyzer.scanner import scan_excel_files


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


def _create_files(directory: Path, filenames: list[str]):
    """Helper to create empty files in a directory."""
    for name in filenames:
        (directory / name).touch()


class TestScanExcelFiles:
    """Tests for scan_excel_files function."""

    def test_finds_xlsx_files(self, temp_dir):
        """scan_excel_files should find .xlsx files."""
        _create_files(temp_dir, ["test1.xlsx", "test2.xlsx"])
        result = scan_excel_files(str(temp_dir))
        assert len(result) == 2
        assert all(f.suffix == ".xlsx" for f in result)

    def test_finds_xls_files(self, temp_dir):
        """scan_excel_files should find .xls files."""
        _create_files(temp_dir, ["test1.xls", "test2.xls"])
        result = scan_excel_files(str(temp_dir))
        assert len(result) == 2
        assert all(f.suffix == ".xls" for f in result)

    def test_finds_both_xlsx_and_xls(self, temp_dir):
        """scan_excel_files should find both .xlsx and .xls files."""
        _create_files(temp_dir, ["file1.xlsx", "file2.xls"])
        result = scan_excel_files(str(temp_dir))
        assert len(result) == 2

    def test_excludes_temp_files(self, temp_dir):
        """scan_excel_files should exclude ~$ temporary files."""
        _create_files(temp_dir, ["normal.xlsx", "~$temp.xlsx", "~$temp.xls"])
        result = scan_excel_files(str(temp_dir))
        assert len(result) == 1
        assert result[0].name == "normal.xlsx"

    def test_excludes_non_excel_files(self, temp_dir):
        """scan_excel_files should not return non-Excel files."""
        _create_files(temp_dir, ["readme.txt", "data.csv", "image.png", "real.xlsx"])
        result = scan_excel_files(str(temp_dir))
        assert len(result) == 1
        assert result[0].name == "real.xlsx"

    def test_returns_sorted_by_filename(self, temp_dir):
        """scan_excel_files should return files sorted by filename."""
        _create_files(temp_dir, ["charlie.xlsx", "alpha.xlsx", "bravo.xls"])
        result = scan_excel_files(str(temp_dir))
        names = [f.name for f in result]
        assert names == ["alpha.xlsx", "bravo.xls", "charlie.xlsx"]

    def test_empty_directory_returns_empty_list(self, temp_dir):
        """scan_excel_files should return empty list for empty directory (Req 1.3)."""
        result = scan_excel_files(str(temp_dir))
        assert result == []

    def test_directory_with_no_excel_files(self, temp_dir):
        """scan_excel_files should return empty list when no Excel files exist (Req 1.3)."""
        _create_files(temp_dir, ["readme.txt", "data.csv", "script.py"])
        result = scan_excel_files(str(temp_dir))
        assert result == []

    def test_returns_path_objects(self, temp_dir):
        """scan_excel_files should return Path objects."""
        _create_files(temp_dir, ["test.xlsx"])
        result = scan_excel_files(str(temp_dir))
        assert all(isinstance(f, Path) for f in result)

    def test_does_not_scan_subdirectories(self, temp_dir):
        """scan_excel_files should only scan the top-level directory, not subdirectories."""
        _create_files(temp_dir, ["top.xlsx"])
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()
        _create_files(sub_dir, ["nested.xlsx"])
        result = scan_excel_files(str(temp_dir))
        assert len(result) == 1
        assert result[0].name == "top.xlsx"
