# Excel Interface Analyzer

Excel Interface設計書（インターフェース設計書）を自動解析し、EBSテーブル定義情報を抽出するPythonツールです。SAP AI Core の Claude モデルを使用して、構造化されたデータ抽出を実現します。

## 機能概要

- **バッチ処理**: `input/` フォルダ内の複数のExcelファイルを自動検出・一括処理
- **データクリーニング**: 削除線・対角叉などの削除マークを自動検出し、有効なデータのみを抽出
- **AI解析**: SAP AI Core の Claude モデルによる高精度な構造化データ抽出
- **Excel出力**: 指定フォーマットに従った結果Excelファイルの自動生成
- **リトライ機能**: API呼び出し失敗時の自動リトライ（指数バックオフ）

## システム要件

- Python 3.10 以上
- SAP AI Core アカウントとデプロイ済みの Claude モデル
- Windows / macOS / Linux

## インストール

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、SAP AI Core の認証情報を設定します：

```env
AICORE_AUTH_URL=https://your-auth-url.authentication.sap.hana.ondemand.com/oauth/token
AICORE_CLIENT_ID=your-client-id
AICORE_CLIENT_SECRET=your-client-secret
AICORE_BASE_URL=https://api.ai.your-region.aws.ml.hana.ondemand.com/v2
AICORE_RESOURCE_GROUP=your-resource-group
AICORE_DEPLOYMENT_ID=your-deployment-id
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
├── analyzer/              # コアモジュール
│   ├── ai_analyzer.py    # AI解析・プロンプト構築
│   ├── cleaner.py        # データクリーニング
│   ├── config.py         # 設定管理
│   ├── logger.py         # ログ管理
│   ├── parser.py         # AI応答パース
│   ├── reader.py         # Excel読取（削除線・対角叉検出）
│   ├── sap_client.py     # SAP AI Core クライアント
│   ├── scanner.py        # ファイルスキャン
│   └── writer.py         # Excel出力
├── input/                 # 入力フォルダ（Excelファイル配置）
├── output/                # 出力フォルダ（結果Excel・ログ）
├── main.py               # メインエントリーポイント
├── run.bat               # Windows実行用バッチファイル
├── requirements.txt      # 依存パッケージ
└── .env                  # 環境変数設定（要作成）
```

## 入力ファイル形式

- **対応形式**: `.xlsx`, `.xlsm`
- **削除マーク検出**:
  - 削除線（strikethrough）
  - 対角叉（diagonal cross: diagonalUp + diagonalDown）
  - 部分削除線（リッチテキスト内の一部のみ削除線）

## 出力ファイル形式

出力Excelファイルは以下のカラム構造で生成されます：

| No. | 文書管理番号 | IF名 | EBSテーブル名 | EBSテーブルID | 項目ID | 項目名 | 桁数 |
|-----|------------|------|--------------|--------------|--------|--------|------|

ファイル名: `EBS定義書_抽出結果_YYYYMMDD_HHMMSS.xlsx`

## ログ

実行ログは以下の場所に出力されます：
- コンソール（標準出力）
- `output/` フォルダ内のログファイル

## トラブルシューティング

### Python が見つからない

```
[ERROR] Python not found. Please install Python first.
```

→ Python 3.10 以上をインストールしてください

### .env ファイルが見つからない

```
[ERROR] .env file not found.
```

→ プロジェクトルートに `.env` ファイルを作成し、SAP AI Core の認証情報を設定してください

### Excel ファイルが見つからない

```
[WARNING] No Excel files found in input folder.
```

→ `input/` フォルダに `.xlsx` または `.xlsm` ファイルを配置してください

### AI 呼び出しエラー

```
[ERROR] AI呼び出し全リトライ失敗
```

→ `.env` の認証情報が正しいか確認してください  
→ SAP AI Core のデプロイメントが稼働中か確認してください  
→ ネットワーク接続を確認してください

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
- **openpyxl**: Excel読取・書込
- **requests**: HTTP通信
- **python-dotenv**: 環境変数管理
- **pytest**: ユニットテスト
- **hypothesis**: プロパティベーステスト

## ライセンス

[ライセンス情報を記載]

## 貢献

[貢献ガイドラインを記載]

## サポート

問題が発生した場合は、以下の情報を含めて Issue を作成してください：
- エラーメッセージ
- 実行環境（OS、Python バージョン）
- 入力ファイルのサンプル（機密情報を除く）
- ログファイル
