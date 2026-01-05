# BoothList

BOOTHの購入アイテムやウィッシュリストを収集・整理し、検索・フィルタリング・可視化できる静的ダッシュボードを生成するツールです。

[デモサイト (GitHub Pages)](https://kafka2306.github.io/boothitemmanager/)

## 特長

- **多角的なデータ収集**:
  - `input/` ディレクトリ内のMarkdown/CSV/YAMLファイルからアイテムリストを読み込み
  - Chrome履歴からの抽出機能 (`src/boothlist/chrome_history.py`)
  - 商品ページからのメタデータ（画像、価格、ショップ名など）自動スクレイピング
- **高度な正規化**:
  - 表記ゆれの統一
  - カテゴリの自動分類と整理
- **高速なダッシュボード**:
  - インクリメンタルな全文検索
  - カテゴリやタグによるフィルタリング
  - 静的HTML出力（GitHub Pages等でホスティング可能）

## 必要要件

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- [go-task](https://taskfile.dev/) (推奨)

## 使い方

### 1. セットアップ

依存関係をインストールします。

```bash
uv sync
```

### 2. 設定

`config.yaml` を編集して、入力データの場所や除外URLなどを設定します。

### 3. ビルド

データを収集し、ダッシュボードを生成します。生成物は `dist/` ディレクトリに出力されます。

```bash
task build
```

### 4. プレビュー

生成されたダッシュボードをローカルサーバーで確認します。

```bash
task serve
```

ブラウザで `http://localhost:8080` にアクセスしてください。

## 開発コマンド

`Taskfile.yml` に定義された開発用コマンドを利用できます。

- **Lint**: `task lint` (Ruffによる静的解析)
- **Format**: `task format` (Ruffによるフォーマット)
- **Clean**: `task clean` (ビルド成果物の削除)
- **Clean Cache**: `task clean-cache` (メタデータキャッシュの削除)

## プロジェクト構成

- `src/boothlist/`: ソースコード
  - `main.py`: アプリケーションのエントリーポイント
  - `input_loader.py`: 各種ソースからのデータ読み込み
  - `scrape.py`: Webスクレイピングとキャッシュ制御
  - `normalize.py`: データのクレンジングと正規化ロジック
  - `export.py`: HTMLダッシュボードおよびJSONデータの生成
  - `chrome_history.py`: Chrome履歴データの解析
- `dist/`: 生成された静的サイト（公開用）
- `input/`: 入力データ（Markdown, CSVなど）