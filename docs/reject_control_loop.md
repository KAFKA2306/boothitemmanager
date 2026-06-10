# REJECT 時の制御ループ設計（無限ループ防止）

メインエージェントが却下（REJECT）判定を下した際の、安全な再実行ループの設計仕様です。無限ループを防ぐための制約を含みます。

## 1. 状態遷移モデル（State Machine）
- `START` ➡️ `EXECUTE` ➡️ `VERIFY` ➡️ `AUDIT` ➡️ `ACCEPT` または `REJECT`
- `REJECT` 判定時は `EXECUTE` に戻り、リトライカウンターをインクリメントします。

## 2. 絶対停止ルール（Zero-Fat 制約）
- **最大リトライ回数**: `MAX_RETRIES = 3`
- 3回連続で `REJECT` された場合、即座に `HALT`（完全停止）し、ユーザーによる手動介入を要求します。
- 曖昧な再実行処理や、例外の握りつぶしは禁止します（Crash-Driven Development に準拠）。

## 3. エスカレーション・フロー
1. **1回目 REJECT**: 該当エージェントに対して `TestBlock` の差分ログをフィードバックし、再実行を指示。
2. **2回目 REJECT**: 別のアプローチ（異なるアルゴリズムやAPI設計）による解決を強制。
3. **3回目 REJECT**: `HaltException` を発生させ、システム全体を即時停止。

## 4. ループ追跡（Traceability）
すべての再実行履歴は、`trace_id` にリトライ回数を付与して記録します。
例: `trace_123_retry_1` ➡️ `trace_123_retry_2`
