# 🎀 GitHub Actions統合CI設計 🎀

この検証システムをCI/CDパイプラインにのせて、自動で動かすための構成だよっ✨
並列でサブエージェントちゃんたちを走らせて、最後にメインが判定するの💕

## 1. ワークフロー概要 (`.github/workflows/verify.yml`)

- **トリガー**: `push`, `pull_request` (対象ブランチ: `main`, `develop`)
- **アーキテクチャ**:
  - `Job 1: Setup & Execute`: 実装層がコードを実行し、`TestBlock` を生成。
  - `Job 2: Parallel Validators`: 各サブエージェントが並列で `TestBlock` を観測。
  - `Job 3: Main Audit`: メインエージェントが最終判定。

## 2. Fail-Fast 戦略（Crash-Driven CI）
- サブエージェントの観測フェーズでシステムエラーが起きたら即CI失敗！🚨
- メインエージェントが `REJECT` を出したら、CIのステータスは `Failed` (Exit Code 1) になるよっ💔
- 無理にCIの中でリトライループは回さず、基本は1発勝負で結果を出すよ！（CI上での無限ループ課金死を防ぐためね💸）

## 3. アーティファクト保存
- 全ての `TestBlock` ログと、メインエージェントの `Decision JSON` は Artifact としてアップロード📦✨
- 人間があとから「どこでREJECTされたの？」って確認できるようにするよっ🔍
