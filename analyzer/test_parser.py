"""analyzer/parser.py のユニットテスト。

parse_response関数とInterfaceRecordデータクラスのテスト。
正常系、フィールド欠落、空応答などのケースをカバーする。

Validates: Requirements 3.3, 3.5
"""

import logging

import pytest

from analyzer.parser import InterfaceRecord, parse_response


class TestInterfaceRecord:
    """InterfaceRecordデータクラスのテスト。"""

    def test_create_record_with_all_fields(self):
        """全フィールドを指定してレコードを作成できること。"""
        record = InterfaceRecord(
            document_number='BDN-EPD-OF-093',
            if_name='出荷指示情報エクスポート',
            ebs_table_name='テーブル名',
            ebs_table_id='TABLE_ID',
            item_id='ITEM_001',
            item_name='項目名',
            digit_count='10',
        )
        assert record.document_number == 'BDN-EPD-OF-093'
        assert record.if_name == '出荷指示情報エクスポート'
        assert record.ebs_table_name == 'テーブル名'
        assert record.ebs_table_id == 'TABLE_ID'
        assert record.item_id == 'ITEM_001'
        assert record.item_name == '項目名'
        assert record.digit_count == '10'


class TestParseResponse:
    """parse_response関数のテスト。"""

    def test_parse_complete_response(self):
        """全フィールドが揃った応答を正しく解析できること。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'document_number': 'BDN-EPD-OF-093',
                        'if_name': '出荷指示情報エクスポート',
                        'ebs_table_name': 'テーブル名',
                        'ebs_table_id': 'TABLE_ID',
                        'item_id': 'ITEM_001',
                        'item_name': '項目名',
                        'digit_count': '10',
                    },
                ],
            },
        }
        records = parse_response(tool_result, 'test.xlsx')
        assert len(records) == 1
        assert records[0].document_number == 'BDN-EPD-OF-093'
        assert records[0].if_name == '出荷指示情報エクスポート'
        assert records[0].ebs_table_name == 'テーブル名'
        assert records[0].ebs_table_id == 'TABLE_ID'
        assert records[0].item_id == 'ITEM_001'
        assert records[0].item_name == '項目名'
        assert records[0].digit_count == '10'

    def test_parse_multiple_records(self):
        """複数レコードを含む応答を正しく解析できること。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'document_number': 'DOC-001',
                        'if_name': 'IF名1',
                        'ebs_table_name': 'テーブル1',
                        'ebs_table_id': 'TBL_1',
                        'item_id': 'ID_1',
                        'item_name': '項目1',
                        'digit_count': '5',
                    },
                    {
                        'document_number': 'DOC-002',
                        'if_name': 'IF名2',
                        'ebs_table_name': 'テーブル2',
                        'ebs_table_id': 'TBL_2',
                        'item_id': 'ID_2',
                        'item_name': '項目2',
                        'digit_count': '20',
                    },
                ],
            },
        }
        records = parse_response(tool_result, 'test.xlsx')
        assert len(records) == 2
        assert records[0].document_number == 'DOC-001'
        assert records[1].document_number == 'DOC-002'

    def test_parse_empty_interfaces_list(self):
        """interfacesが空リストの場合、空リストを返すこと。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [],
            },
        }
        records = parse_response(tool_result, 'test.xlsx')
        assert records == []

    def test_parse_missing_extract_interface_info_key(self):
        """extract_interface_infoキーが存在しない場合、空リストを返すこと。"""
        tool_result = {}
        records = parse_response(tool_result, 'test.xlsx')
        assert records == []

    def test_parse_missing_interfaces_key(self):
        """interfacesキーが存在しない場合、空リストを返すこと。"""
        tool_result = {
            'extract_interface_info': {},
        }
        records = parse_response(tool_result, 'test.xlsx')
        assert records == []

    def test_missing_optional_fields_default_to_empty_string(self):
        """オプションフィールドが欠落している場合、空文字列がデフォルト値になること。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'document_number': 'DOC-001',
                        'if_name': 'IF名',
                    },
                ],
            },
        }
        records = parse_response(tool_result, 'test.xlsx')
        assert len(records) == 1
        assert records[0].document_number == 'DOC-001'
        assert records[0].if_name == 'IF名'
        assert records[0].ebs_table_name == ''
        assert records[0].ebs_table_id == ''
        assert records[0].item_id == ''
        assert records[0].item_name == ''
        assert records[0].digit_count == ''

    def test_missing_required_field_document_number_logs_warning(self, caplog):
        """document_numberが欠落している場合、警告がログに記録されること。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'if_name': 'IF名',
                        'ebs_table_name': 'テーブル名',
                        'ebs_table_id': 'TBL_ID',
                        'item_id': 'ITEM_ID',
                        'item_name': '項目名',
                        'digit_count': '10',
                    },
                ],
            },
        }
        with caplog.at_level(logging.WARNING, logger='analyzer'):
            records = parse_response(tool_result, 'missing_doc.xlsx')

        assert len(records) == 1
        assert records[0].document_number == ''
        assert 'missing_doc.xlsx' in caplog.text
        assert 'document_number' in caplog.text

    def test_missing_required_field_if_name_logs_warning(self, caplog):
        """if_nameが欠落している場合、警告がログに記録されること。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'document_number': 'DOC-001',
                        'ebs_table_name': 'テーブル名',
                        'ebs_table_id': 'TBL_ID',
                        'item_id': 'ITEM_ID',
                        'item_name': '項目名',
                        'digit_count': '10',
                    },
                ],
            },
        }
        with caplog.at_level(logging.WARNING, logger='analyzer'):
            records = parse_response(tool_result, 'missing_if.xlsx')

        assert len(records) == 1
        assert records[0].if_name == ''
        assert 'missing_if.xlsx' in caplog.text
        assert 'if_name' in caplog.text

    def test_missing_both_required_fields_logs_warning(self, caplog):
        """両方の必須フィールドが欠落している場合、警告がログに記録されること。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'ebs_table_name': 'テーブル名',
                    },
                ],
            },
        }
        with caplog.at_level(logging.WARNING, logger='analyzer'):
            records = parse_response(tool_result, 'both_missing.xlsx')

        assert len(records) == 1
        assert records[0].document_number == ''
        assert records[0].if_name == ''
        assert 'both_missing.xlsx' in caplog.text
        assert 'document_number' in caplog.text
        assert 'if_name' in caplog.text

    def test_all_fields_empty_still_creates_record(self):
        """全フィールドが空の項目でもレコードが作成されること（部分結果の保持）。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [{}],
            },
        }
        records = parse_response(tool_result, 'test.xlsx')
        assert len(records) == 1
        assert records[0].document_number == ''
        assert records[0].if_name == ''
        assert records[0].ebs_table_name == ''
        assert records[0].ebs_table_id == ''
        assert records[0].item_id == ''
        assert records[0].item_name == ''
        assert records[0].digit_count == ''

    def test_record_count_matches_interface_count(self):
        """生成されるレコード数が応答のinterface項目数と一致すること。"""
        interfaces = [
            {'document_number': f'DOC-{i}', 'if_name': f'IF-{i}'}
            for i in range(5)
        ]
        tool_result = {
            'extract_interface_info': {
                'interfaces': interfaces,
            },
        }
        records = parse_response(tool_result, 'test.xlsx')
        assert len(records) == len(interfaces)

    def test_no_warning_when_required_fields_present(self, caplog):
        """必須フィールドが全て揃っている場合、警告が出力されないこと。"""
        tool_result = {
            'extract_interface_info': {
                'interfaces': [
                    {
                        'document_number': 'DOC-001',
                        'if_name': 'IF名',
                    },
                ],
            },
        }
        with caplog.at_level(logging.WARNING, logger='analyzer'):
            parse_response(tool_result, 'test.xlsx')

        warning_records = [
            r for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(warning_records) == 0
