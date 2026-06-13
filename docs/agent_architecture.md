# 🌸 サブエージェント監督型 実行アーキテクチャだょ！ 🌸

このシステムは、お互いに監視し合う「検証システム」になっているよぉ！(⑅•ᴗ•⑅)◜..°♡

## 🎀 1. 統治構造と役割
システムは3つのレイヤーでうごいているよ🍭

1. **実装層 (Implementation)**: データの処理やAPIの生成を行って、実行結果を `TestBlock` として出力するよ！
2. **検証サブエージェント群 (Validators)**: 局所的な観測（DB変更の監視など）をして、結果をメインに報告するの（自分で合否は決めないよ）。
3. **メインエージェント (Audit Core)**: すべての報告をうけて、最終的な **ACCEPT** または **REJECT** の判定を下す唯一のボスエージェントだよっ✨

## 🐾 2. Test Block システム (不変条件の検証)
すべての処理結果は `TestBlock` 形式で記録され、事前状態と事後状態が正しいか数学的・論理的に証明されるの！

```text
TestBlock {
  trace_id,
  input,
  pre_state,
  action,
  expected_state,
  actual_state,
  diff,
  result // メインエージェントが決定するよ！
}
```

## 🍭 3. 監査・REJECTの絶対ルール
以下のどれか1つでも当てはまると、即座に **REJECT** になっちゃうよ！
- 事前・事後状態の不一致 (`expected_state` と `actual_state` が1バイトでも違う)
- `SchemaRegistry.lock()` されたスキーマへの違反
- タグやアバターの関連グラフ構造の破壊
- 実行ログの欠損やトレースIDの断絶
- エラーを隠す `try-catch` の使用

## ✉️ 4. エージェント通信規約 (Protocol)
エージェント同士のやり取りは、自然言語ではなく必ず構造化されたフォーマット（`Message`）で行うよ！
`Message { from_agent, to_agent, trace_id, payload, state_ref }`

## ⚙️ 5. MVP実行フロー
1. スキーマ固定 ➔ 2. Crawler起動 ➔ 3. Rawデータ蓄積 ➔ 4. Normalizer実行 ➔ 5. DB構築 ➔ 6. Graph構築 ➔ 7. Search Index構築 ➔ 8. API公開 ➔ 9. UI生成 ➔ 10. Validator検証

## 🚨 メインエージェント (Audit Core) プロンプト仕様
メインエージェントは以下のプロンプトで動くよ：
- **役割**: 提出された `TestBlock` やログを厳密にチェックし、合否判定を下す。
- **制約**: 自分自身でコードを直したり、推測で承認（ACCEPT）することは禁止。
- **出力形式**: JSONで判定（`decision: ACCEPT | REJECT`）、理由（`reasoning`）、違反ルール（`failed_rules`）、必要なアクション（`required_actions`）を出力するよぉ！
