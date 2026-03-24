# Excel Interface Analyzer

Excel Interface設計書（インターフェース設計書）を自動解析し、EBSテーブル定義情報を抽出するPythonツールです。SAP AI Core の Claude モデルを使用して、構造化されたデータ抽出と新フォーマットへの変換を実現します。

## 機能概要

- **バッチ処理**: `input/` フォルダ内の複数のExcelファイルを自動検出・一括処理
- **削除マーク検出**: 削除線・対角叉・部分削除線を自動検出し、有効なデータのみを抽出
- **二段階AI解析**: Phase 1でシート構造・列情報を識別、Phase 2で項目データを抽出
- **抽出結果出力**: EBSテーブル定義情報をExcelファイルに出力（`output/extracted/`）
- **新フォーマット出力**: IFマッピング定義書テンプレートに自動転記（`output/formatted/`）
- **参考ファイル連携**: `本社EBS現行IF一覧` から送受信システム情報をファジーマッチで取得
- **リトライ機能**: API呼び出し失敗時の自動リトライ（指数バックオフ）

## システム要件

- Python 3.10 以上
- SAP AI Core アカウントとデプロイ済みの Claude モデル
- Windows / macOS / Linux

## インストール

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、SAP AI Core の認証情報を設定します：

```env
AICORE_AUTH_URL=https://your-auth-url.authentication.sap.hana.ondemand.com/oauth/token
AICORE_CLIENT_ID=your-client-id
AICORE_CLIENT_SECRET=your-client-secret
AICORE_BASE_URL=https://api.ai.your-region.aws.ml.hana.ondemand.com/v2
AICORE_RESOURCE_GROUP=your-resource-group
AICORE_DEPLOYMENT_ID=your-deployment-id

# オプション（デフォルト値あり）
INPUT_DIR=input
OUTPUT_DIR=output
PHASE1_HEAD_ROWS=30
MAX_CHUNK_ROWS=100
TEMPLATE_PATH=reference/IF抽出_新フォーマット.xlsx
REFERENCE_PATH=reference/本社EBS現行IF一覧.xlsx
```

## 使用方法

### Windows ユーザー（推奨）

1. Interface設計書のExcelファイルを `input/` フォルダに配置
2. `run.bat` をダブルクリックして実行
3. 処理完了後、`output/` フォルダに結果ファイルが生成されます

### コマンドライン実行

```bash
python main.py
```

## プロジェクト構成

```
.
├── analyzer/
│   ├── ai_analyzer.py    # AI解析・プロンプト構築（二段階処理）
│   ├── cleaner.py        # データクリーニング
│   ├── config.py         # 設定管理（.env読み込み）
│   ├── formatter.py      # 新フォーマットExcel出力
│   ├── logger.py         # ログ管理
│   ├── parser.py         # AI応答パース・InterfaceRecord定義
│   ├── reader.py         # Excel読取（削除線・対角叉・部分削除線検出）
│   ├── sap_client.py     # SAP AI Core クライアント
│   ├── scanner.py        # ファイルスキャン（xlsx/xlsm/xls対応）
│   └── writer.py         # 抽出結果Excel出力
├── input/                # 入力フォルダ（設計書Excelを配置）
├── output/
│   ├── extracted/        # 抽出結果Excel（EBS定義書_抽出結果_*.xlsx）
│   ├── formatted/        # 新フォーマットExcel（IF抽出_*.xlsx）
│   └── analyzer.log      # 実行ログ
├── reference/
│   ├── IF抽出_新フォーマット.xlsx     # 出力テンプレート
│   └── 本社EBS現行IF一覧.xlsx        # 送受信システム参照ファイル
├── main.py               # メインエントリーポイント
├── run.bat               # Windows実行用バッチファイル
├── requirements.txt      # 依存パッケージ
└── .env                  # 環境変数設定（要作成）
```

## 入力ファイル形式

- **対応形式**: `.xlsx`, `.xlsm`, `.xls`
- **削除マーク検出**:
  - 削除線（strikethrough）
  - 対角叉（diagonal cross: diagonalUp + diagonalDown）
  - 部分削除線（リッチテキスト内の一部のみ削除線）

## 出力ファイル

### 抽出結果（`output/extracted/`）

EBSテーブル定義情報を一覧形式で出力します。

| No. | 文書管理番号 | IF名 | EBSテーブル名 | EBSテーブルID | 項目ID | 項目名 | 桁数 |
|-----|------------|------|--------------|--------------|--------|--------|------|

ファイル名: `EBS定義書_抽出結果_YYYYMMDD_HHMMSS.xlsx`

### 新フォーマット（`output/formatted/`）

入力ファイルごとに `reference/IF抽出_新フォーマット.xlsx` テンプレートをベースに生成します。

- **表紙**: IF名称・日付を記入
- **改訂履歴**: 作成日を記入
- **対象IF**: `本社EBS現行IF一覧` からファジーマッチで送受信システム（FROM/TO）を取得して記入
- **IFマッピング定義**: AI抽出結果（項目名・テーブルID・項目ID・データ型・桁数・項目説明等）を記入

ファイル名: `IF抽出_<元ファイル名>.xlsx`

## AI解析の仕組み

### Phase 1（構造識別）
全シートの先頭 `PHASE1_HEAD_ROWS`（デフォルト30）行を一括送信し、以下を識別します：
- 文書管理番号・IF名
- データ項目シートの特定
- 各シートの列構造（テーブル名列・テーブルID列・項目ID列・桁数列）

### Phase 2（項目抽出）
Phase 1 で識別した列のみに絞り込んだデータ行を `MAX_CHUNK_ROWS`（デフォルト100）行単位で分割し、以下を抽出します：
- EBSテーブル名・テーブルID
- 項目ID・項目名・項目説明
- データ型・桁数・必須/任意・キー区分 等

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| `Python not found` | Python 3.10 以上をインストール |
| `.env file not found` | プロジェクトルートに `.env` を作成 |
| `No Excel files found` | `input/` フォルダにExcelファイルを配置 |
| `AI呼び出し全リトライ失敗` | `.env` の認証情報・ネットワーク・デプロイメント状態を確認 |
| 新フォーマットが生成されない | `reference/` フォルダにテンプレートと参照ファイルが存在するか確認 |

## テスト

```bash
# 全テスト実行
pytest

# 特定モジュールのテスト
pytest analyzer/test_reader.py -v

# カバレッジ付き実行
pytest --cov=analyzer --cov-report=html
```

## 技術スタック

- **Python 3.10+**
- **openpyxl**: xlsx/xlsm 読取・書込
- **xlrd**: xls 読取
- **requests**: HTTP通信
- **python-dotenv**: 環境変数管理
- **pytest**: ユニットテスト
