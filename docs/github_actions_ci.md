# GitHub Actions 統合 CI 設計

この検証システムを CI/CD パイプライン上で自動稼働させるための構成案です。
並列でサブエージェントを実行して検証を行い、最終段階でメインエージェントが判定を下します。

## 1. ワークフロー概要 (`.github/workflows/verify.yml`)

- **トリガー**: `push`, `pull_request` (対象ブランチ: `main`, `develop`)
- **アーキテクチャ**:
  - `Job 1: Setup & Execute`: 実装層がコードを実行し、`TestBlock` を生成。
  - `Job 2: Parallel Validators`: 各サブエージェントが並列で `TestBlock` を観測。
  - `Job 3: Main Audit`: メインエージェントが最終判定。

## 2. Fail-Fast 戦略（Crash-Driven CI）
- サブエージェントの観測フェーズでシステムエラーが発生した場合は即座に CI を失敗とします。
- メインエージェントが `REJECT` と判定した場合は、CI のステータスを `Failed` (Exit Code 1) とします。
- CI 内部での無駄な自動リトライループは行わず、原則として 1 回の実行で結果を確定させます（CI リソースの過剰消費を防ぐためです）。

## 3. アーティファクト保存
- すべての `TestBlock` ログおよびメインエージェントの `Decision JSON` はアーティファクトとしてアップロードします。
- 開発者が後から却下（REJECT）の理由を確認し、検証・調査できるように記録を残します。
