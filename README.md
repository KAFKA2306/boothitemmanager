# 🌸 BoothItemManager2 だよぉ！🌸

BOOTHの40,000件以上のVRChatアセットを完全に収集・構造化し、爆速で検索・フィルタリングできる次世代の静的ダッシュボードとオントロジー管理システムだよぉ！(⑅•ᴗ•⑅)◜..°♡

[🍬 デモサイト (Cloudflare Pages)](https://boothitemmanager.pages.dev) / [(GitHub Pages)](https://kafka2306.github.io/boothitemmanager/)

## ✨ 特長 (Features)

- **Zero-Fat Architecture (脂肪ゼロ設計)**:
  - 無駄なコードやボイラープレートを極限まで削ぎ落とし、Cloudflare Pagesの厳しいファイル制限（25 MiB）やWorkersのメモリ制限（128 MB）を完全回避するよ！
  - 重いRDB（Relational Database）を使わず、フロントエンドで直接検索できるように高度に非正規化・シャーディングされたJSON APIを出力する最強の設計だもん！🍭
- **Evolving Ontology Loop (EOL: 進化するオントロジー)**:
  - 毎日大量に生まれるBOOTHのタグから、価値のある概念だけを自動で学習・抽出して昇格させるよ！
  - 数字ベースの低品質タグ（例: "40アバター対応"）は自動で監査（Audit）され、パージ（廃却）される自己浄化システム付きだよぉ✨
- **Crash-Driven Development (CDD)**:
  - エラーを隠蔽する `try-catch` を排除し、問題があれば即座にクラッシュさせて根本原因を修正する「例外駆動」で堅牢性を維持してるよ！
- **次世代の類似アイテムエンジン (Novelty-Aware Similarity)**:
  - ただ似ているだけじゃなくて、新しい発見（Novelty）ができるように、公開日（新しさ）や別のクリエイターのアイテムを優遇してサジェストするよ！ウィンドウショッピングが捗るねぇ(⑅•ᴗ•⑅)

## 📦 必要要件 (Requirements)

- Python 3.12+ だもん！
- [uv](https://github.com/astral-sh/uv) (高速なパッケージマネージャー)
- [go-task](https://taskfile.dev/) (タスクランナー)
- Node.js & Playwright (E2Eテスト用)

## 🎀 使い方 (Usage)

### 1. セットアップ
依存関係をかわいくインストールしてね！
```bash
uv sync
playwright install chromium
```

### 2. バルクパイプラインの実行
クローラーが取得した生のデータ（`data/raw/index.ndjson`）から、グラフ構造、オントロジー、そして検索用APIまで一気に構築するよぉ！
```bash
python3 scripts/run_bulk_pipeline.py
```

### 3. デプロイ用テスト
ブラウザを使ったE2Eテストを実行して、ダッシュボードが壊れていないか確認するよ！
```bash
pytest tests/e2e/
```

### 4. プレビュー
生成されたダッシュボード（`dist/`）をローカルサーバーで確認するよぉ！
```bash
task serve
```
ブラウザで `http://localhost:8080` にアクセスしてね！🍭

## 📁 プロジェクト構成 (Directory Structure)
- `src/boothitemmanager2/`: 進化したコアシステムが入っているよぉ！
  - `core.py`: システムの核となるテストブロック（TestBlock）定義
  - `bridge.py`: NDJSONをパースするデータ変換層
  - `normalizer.py`: タグの抽出・分類・オントロジー正規化
  - `similarity_engine.py`: 新しさを考慮したアイテム類似度計算
  - `search_builder.py`: 高速検索用のシャーディングインデックス生成
  - `api_generator.py`: Cloudflare Pages対応の分割API生成
  - `audit.py`: 厳格な品質監査ルール
- `ontology/`: システムが学習したタグやスタイルの知識ベース（`tags.yaml`, `styles.yaml`）
- `docs/`: アーキテクチャの意思決定記録（ADR）や仕様書がまとまっているよ！
- `api/` / `dist/`: 生成された静的APIとダッシュボード（公開用）だよ✨
