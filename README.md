# 🌸 BoothItemManager2 だよぉ！ 🌸

BOOTHの40,000件以上のVRChatアセットを完全に収集・構造化し、爆速で検索・フィルタリングできる次世代の静的ダッシュボードとオントロジー管理システムだよぉ！(⑅•ᴗ•⑅)◜..°♡

👉 **AIエージェントさんへ**: プロジェクトの全体構造は [llms.txt](file:///home/kafka/projects/boothitemmanager/llms.txt) を、開発ガイドは [AGENTS.md](file:///home/kafka/projects/boothitemmanager/AGENTS.md) を最初に読んでねっ✨

## ✨ 特長 (Features)
- **Zero-Fat Architecture**: 無駄を極限まで削ぎ落とし、Cloudflare Pagesの25 MiB制限を回避する超軽量設計！
- **Evolving Ontology Loop**: 収集したタグから価値ある概念を自動学習し、不要なタグ（"40アバター対応"等）を監査でパージ！
- **Crash-Driven Development**: `try-catch` を排除し、問題があれば即座にクラッシュさせて根本修正する堅牢設計。
- **Novelty-Aware Similarity**: 新しさと多様性を重視した、ウィンドウショッピングが楽しくなる類似サジェスト！

## 📦 必要要件 (Requirements)
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (高速パッケージマネージャー)
- [go-task](https://taskfile.dev/) (タスクランナー)

## 🎀 使い方 (Usage)
```bash
# 1. 依存関係のインストール
uv sync
playwright install chromium

# 2. パイプライン実行（ビルド）
task build

# 3. テストとプレビュー
task check
task serve  # http://localhost:8080 で確認できるよ！
```

## 📁 フォルダ構成 (Directory)
- `src/boothitemmanager2/`: 進化したコアシステム（ノーマライザ、検索ビルダー等）
- `ontology/`: タグやスタイルの知識ベース（`tags.yaml`等）
- `docs/`: 仕様書や意思決定ログ（ADR）
- `api/` / `dist/`: 生成された静的APIとダッシュボード
