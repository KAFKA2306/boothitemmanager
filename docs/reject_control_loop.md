# 🎀 REJECT時の制御ループ設計（無限ループ防止） 🎀

メインエージェントちゃんが「ダメっ！」って言ったときの、安全なやり直しループの仕組みだよっ✨ 無限にループしちゃうのを防ぐための絶対ルールね💕

## 1. 状態遷移モデル（State Machine）
- `START` ➡️ `EXECUTE` ➡️ `VERIFY` ➡️ `AUDIT` ➡️ `ACCEPT` or `REJECT`
- `REJECT`時は `EXECUTE` に戻るけど、ペナルティカウンターが進むよっ！

## 2. 絶対停止ルール（Zero-Fat制約）
- **最大リトライ回数**: `MAX_RETRIES = 3`
- 3回連続で `REJECT` されたら、即座に `HALT`（完全停止）して人間に助けを求めるよっ🚨
- 曖昧な「ちょっと待って再実行」は禁止！例外握りつぶしもダメ絶対🙅‍♀️（Crash-Driven Development）

## 3. エスカレーション・フロー
1. **1回目 REJECT**: 該当エージェントに `TestBlock` の差分ログを添えて再命令💌
2. **2回目 REJECT**: 異なるアプローチ（別アルゴリズムや別API）での解決を強制🔍
3. **3回目 REJECT**: `HaltException` をスローしてシステム全体を即時停止🛑 人間の介入を待つよっ！

## 4. ループ追跡（Traceability）
すべてのやり直しは `trace_id` にリトライ回数を付与して記録するよ📝
例: `trace_123_retry_1` -> `trace_123_retry_2`
