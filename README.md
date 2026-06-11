# 🌸 BoothList だよぉ！🌸

BOOTHの購入アイテムやウィッシュリストを収集・整理し、検索・フィルタリング・可視化できる静的ダッシュボードを自動生成するめっちゃ可愛いツールだよぉ！(⑅•ᴗ•⑅)◜..°♡

[🍬 デモサイト (GitHub Pages)](https://kafka2306.github.io/boothitemmanager/)

## ✨ 特長 (Features)

- **多角的なデータ収集**:
  - `input/` ディレクトリ内のMarkdown/CSV/YAMLファイルからアイテムリストを読み込むよぉ！
  - Chromeの履歴から自動で抽出する機能もあるの (`src/boothlist/chrome_history.py`)
  - 商品ページからメタデータ（画像、価格、ショップ名など）を自動スクレイピングしちゃうよ！
- **高度な正規化**:
  - 表記ゆれを綺麗に統一するよぉ！
  - カテゴリを自動でわかりやすく分類・整理するの🍭
- **高速なダッシュボード**:
  - インクリメンタルな全文検索でサクサク探せるよ！
  - カテゴリやタグによるフィルタリングもバッチリ！
  - 静的HTML出力だから、GitHub Pagesなどで簡単にホスティングできるよぉ✨

## 📦 必要要件 (Requirements)

- Python 3.11+ だもん！
- [uv](https://github.com/astral-sh/uv)
- [go-task](https://taskfile.dev/) (推奨だよぉ！)

## 🎀 使い方 (Usage)

### 1. セットアップ
依存関係をかわいくインストールしてね！
```bash
uv sync
```

### 2. 設定
[config.yaml](file:///home/kafka/projects/boothitemmanager/config.yaml) をお好みで編集して、入力データの場所や除外URLなどを設定してねぇ！

### 3. ビルド
データを収集してダッシュボードを生成するよ！生成物は `dist/` ディレクトリに出力されるの(⑅•ᴗ•⑅)◜..°♡
```bash
task build
```

### 4. プレビュー
生成されたダッシュボードをローカルサーバーで確認するよぉ！
```bash
task serve
```
ブラウザで `http://localhost:8080` にアクセスしてね！🍭

## 🛠️ 開発コマンド (Developer Commands)
[Taskfile.yml](file:///home/kafka/projects/boothitemmanager/Taskfile.yml) に定義された開発用コマンドが使えるよぉ！
- **Lint**: `task lint` (Ruffによる静的解析をするの)
- **Format**: `task format` (Ruffによるフォーマットだよ)
- **Clean**: `task clean` (ビルド成果物をすっきり削除するよ)
- **Clean Cache**: `task clean-cache` (メタデータキャッシュを削除するよ)

## 📁 プロジェクト構成 (Directory Structure)
- `src/boothlist/`: ソースコードが入っているよぉ！
  - `main.py`: アプリケーションのエントリーポイント
  - `input_loader.py`: 各種ソースからのデータ読み込み
  - `scrape.py`: Webスクレイピングとキャッシュ制御
  - `normalize.py`: データのクレンジングと正規化ロジック
  - `export.py`: HTMLダッシュボードおよびJSONデータの生成
  - `chrome_history.py`: Chrome履歴データの解析
- `dist/`: 生成された静的サイト（公開用）だよ✨
- `input/`: 入力データ（Markdown, CSVなど）を置く場所だよぉ！