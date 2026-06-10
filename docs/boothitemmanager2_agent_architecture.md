# BoothItemManager2再現実装：サブエージェント監督型 実行指示書（完全版）

## 0. 基本原則（絶対制約）
本システムは以下を前提とする：
・単一エージェントは禁止
・LLMの完了報告は禁止（信頼しない）
・すべての成果物は外部検証可能であること
・すべての処理はTest Block化されること
・実行と設計は完全分離すること
・メインエージェントのみが最終的な **REJECT（拒否）権限** を持つこと

## 1. 統治構造：REJECT権限付き監査中枢モデル
システムは以下の3層で構成される：

### ① 実装層（Implementation Layer）
・コード実行 / DB更新 / API応答生成
・実行結果をTest Blockとして出力

### ② 検証サブエージェント群（Verification Agents）
・局所的な観測と状態報告のみを実行
・**判定（真偽）は出さない**

### ③ メインエージェント（Audit + REJECT Core）
・唯一の最終判定権限（ACCEPT / REJECT）を保持
・全サブエージェントの結果を統合し、矛盾や仕様違反があれば即REJECT

## 2. エージェント構造（詳細役割）
... (中略: 各エージェントの役割は既存の設計を継承) ...

### ⑦ Validator Agent (検証サブエージェント群の一員)
役割： ・Test Block実行 ・DB差分検証 ・APIレスポンス検証 ・再実行検証
制約： ・書き込み禁止 ・**状態報告のみ（REJECT判断は行わない）**

## 3. REJECTルール（絶対制約）
以下いずれかで即REJECT（軽微エラーは存在しない）：
・Test Blockと実測の不一致
・スキーマ違反 / グラフ構造破壊
・検索結果再現性欠如
・ログ欠損 / トレース不能状態

## 4. 実行・評価フロー
1. **実装層** が処理実行し、**Test Block** を生成
2. 各 **Validator（サブエージェント）** が観測のみ実行し、メインへ報告
3. **メインエージェント** が結果を統合し、仕様と照合
4. **ACCEPT / REJECT** を決定。REJECT時は再実行命令を発行

## 5. Test Blockシステム（中核）
全操作は必ず以下形式に変換される：
`TestBlock { trace_id input pre_state action expected_state actual_state diff result }`
※ `result`（最終成否）はメインエージェントのみが決定する。

... (以下、既存のデータストレージ設計、通信規約等を継続) ...

## 6. データストレージ設計
- **Raw Layer**: RawAssetPage
- **Structured Layer**: Asset / Creator / Tag
- **Graph Layer**: nodes / edges
- **Log Layer**: TestBlockLog / CrawlLog / AccessLog
※すべてappend-only

## 7. エージェント通信規約
すべての通信は以下形式：
`Message { from_agent to_agent trace_id payload state_ref }`
禁止： ・暗黙状態共有 ・自然言語依存 ・非構造通信

## 8. スキーマ固定ルール
実行前に必ず：`SchemaRegistry.lock()`
解除禁止（破壊防止）

## 9. MVP実行順序（監督型）
1. SchemaRegistry固定
2. Crawler Agent起動
3. Rawデータ蓄積
4. Normalizer実行
5. DB構築
6. Graph Builder
7. Search Index構築
8. API公開
9. UI生成
10. Analytics起動
11. Validator常時稼働

## 10. 失敗時ルール（重要）
いかなる失敗も以下処理：
・Test Block再生成 ・該当Agent再実行 ・Coordinatorへ報告のみ（修正は人間 or 上位制御）
禁止： ・自己修正ループ ・推測復旧 ・曖昧補完

## 11. 成功条件（外部検証のみ）
以下が揃ったときのみ成功：
・BOOTHデータが構造化済み ・作者グラフが生成済み ・検索APIが応答 ・ランキング生成 ・流入解析動作 ・Test Block再現可能 ・Validator全通過

## 12. 最重要思想（設計核）
このシステムは「生成AIシステム」ではなく：
**“検証可能な分散実行システム”**
である。

## 13. 詳細設計ドキュメント
本構造に基づく詳細設計については、以下の各ドキュメントを参照すること：
- [REJECT時の制御ループ設計（無限ループ防止）](./reject_control_loop.md)
- [メインエージェントのプロンプト完全仕様](./main_agent_prompt.md)
- [GitHub Actions統合CI設計](./github_actions_ci.md)
- [Test Blockの証明可能性モデル（形式検証寄り）](./test_block_provability.md)
- [監査定義仕様（Audit Checklist）](./audit_checklist.md)
