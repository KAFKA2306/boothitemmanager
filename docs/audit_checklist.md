# DEFINE AUDIT CHECKLIST（監査定義仕様）

メインエージェントが妥協なく厳格に監査を行うための、機械的な監査ルール定義です。推測や曖昧さを排除し、すべて PASS または FAIL の二値判定で評価します。

---

## 1. スキーマ監査（Schema Audit）
対象：DB, API, Test Block構造
- [ ] すべての必須フィールドが存在するか
- [ ] 型が定義（storage.py）と一致しているか
- [ ] NULL許容ルールに違反していないか
- [ ] IDの一意性が保たれているか
- [ ] 外部キー参照（item_id等）が有効か

## 2. データ整合性監査（Data Integrity Audit）
対象：Asset, Creator, Tag
- [ ] 重複レコードが存在しないか
- [ ] 参照切れ（orphan）が存在しないか
- [ ] 欠損フィールド（Itemの必須情報等）がないか
- [ ] 正規化ルール（aliases.yml）に違反していないか

## 3. 実行フロー監査（Pipeline Audit）
対象：Crawler, Normalizer, Graph Builder, Search Index
- [ ] 定義された順序（MVP実行順序）通りか
- [ ] 中間データが欠落していないか
- [ ] ステップスキップがないか
- [ ] 同一入力に対し同一出力か（決定性）

## 4. グラフ構造監査（Graph Audit）
対象：nodes, edges
- [ ] 孤立ノードが許容範囲内か
- [ ] エッジタイプが定義通りか
- [ ] 循環禁止ルールに違反していないか
- [ ] 重複エッジがないか
- [ ] 参照先ノードが存在するか

## 5. 検索再現性監査（Search Audit）
対象：検索結果, ランキング
- [ ] 同一クエリで同一結果が返るか
- [ ] インデックス（search_index.json）と実データが一致しているか
- [ ] ソート順が仕様通りか
- [ ] 欠損結果がないか

## 6. ログ完全性監査（Log Audit）
対象：Test Block Log, Crawl Log, Access Log
- [ ] trace_id の連続性が維持されているか
- [ ] 欠損ログが存在しないか
- [ ] 改ざん痕跡がないか
- [ ] append-only が維持されているか

## 7. Test Block整合性監査（Test Block Audit）
対象：TestBlock構造全体
- [ ] expected_state が仕様から逸脱していないか
- [ ] actual_state が実データと一致しているか
- [ ] diff が正しく計算されているか
- [ ] result がメインエージェントの判定と一致しているか

## 8. クロス監査（Cross Audit）
対象：全システム
- [ ] モジュール間データ矛盾がないか
- [ ] Graph と DB が一致しているか
- [ ] Search 結果と DB が一致しているか
- [ ] Log と実行履歴が一致しているか

---

## 9. 判定ルール（メインエージェント専用）
以下のいずれかが存在すれば **REJECT**：
- FAIL が 1 つでも存在
- 未検証項目が存在
- チェックリスト未適用
- データソース不一致

## 10. 禁止事項
- 重み付け評価（一部の項目を恣意的に看過することを禁止します）
- あいまい評価（厳格な一致を確認し、近似評価を禁止します）
- スコアリング
- 推測補完
- 部分合格

## 11. 出力形式
`AuditChecklistResult { trace_id, category, items[], final_status: PASS | FAIL, reject_reason }`

## 12. システム思想
このチェックリストは「判断基準」ではなく、**“拒否条件の列挙”** です。
