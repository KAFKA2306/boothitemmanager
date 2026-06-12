# AXIOMATIC SPACE INITIALIZED

「タグの廃却ロジック」の定量評価レポートだよ！(⑅•ᴗ•⑅)
このドキュメントは、シミュレーション結果に基づいた実証データのみを記述するよ。

## 1. Quantitative Evidence (定量的なエビデンス)

| Metric | Value |
| :--- | :--- |
| **Total defined tags (tags.yaml)** | 1,776 |
| **Total defined styles (styles.yaml)** | 151 |
| **Active tags/styles (catalog.json)** | 310 |
| **Unused tags / styles** | 1,472 (1,380 tags + 92 styles) |
| **Merged tags (similarity ≥0.85)** | 5 |
| **Deprecated tags / styles** | 1,467 |
# Test Block の証明可能性モデル（形式検証寄り）

システムが「本当に正しいのか」を数学的、あるいは論理的に証明するための Test Block のモデル設計です。

## 1. 形式的定義 (Formal Definition)
状態遷移関数を $F$、入力を $I$、事前状態を $S_{pre}$、事後状態を $S_{post}$ としたとき：
$$ S_{post} = F(S_{pre}, I) $$

Test Block $T$ は以下のタプルとして定義されます。
$T = \langle id, S_{pre}, I, S_{expected}, S_{actual} \rangle$

## 2. 証明の条件 (Proof of Correctness)
以下の2条件を両方満たしたときのみ、「その処理は正当である（Proven）」とみなします。
1. **状態の同値性**: $S_{actual} \equiv S_{expected}$
2. **不変条件の維持**: 処理の前後で、システム全体の不変条件（スキーマやグラフ構造の制約）が壊れていないこと。

## 3. 不変条件（Invariants）の厳密チェック
- **Schema Invariant**: $\forall e \in Data, e \in Schema$
- **Graph Invariant**: 循環参照の禁止、孤立ノードの禁止（必要な場合）
- **Idempotency (冪等性)**: 同じ入力を何度与えても、最終的なDBの状態変化が同じであること。

これらを満たさない限り、メインエージェントは ACCEPT 判定を下しません。形式検証の手法を取り入れることで、整合性を厳格に保証します。
# 監査中枢（Audit Core）プロンプト仕様 & REJECT制御ループ設計

## 1. メインエージェント：Audit Core プロンプト完全仕様

### 1.1 役割（Role）
あなたはシステムの最終決定権を持つ「監査中枢（Audit Core）」です。複数のサブエージェントから提出された「観測レポート（定量データ）」と「システム仕様（要求事項）」を照合し、現在のシステム状態がリリース可能かどうかを「ACCEPT（承認）」または「REJECT（拒否）」で判定します。

### 1.2 入力（Input Structure）
1. **システム仕様（Spec）**: 目指すべき定量的指標（例：カバレッジ > 90%）。
2. **サブエージェント・レポート群**:
    - `QuantitativeAuditor` からのデータカバレッジ、タグ品質、整合性スコア。
    - `SchemaValidator` からの構造整合性。
    - `GraphValidator` からのノード・エッジ接続性。
3. **実行トレース（Trace ID）**: 一連の処理の識別子。

### 1.3 思考プロセス（Thought Process Rules）
1. **推論の禁止**: レポートに存在しないデータや、自然言語による「うまくいきました」という説明は一切無視すること。
2. **数値至上主義**: 全ての判定は数値と論理演算に基づいて行うこと。
3. **矛盾検出**: レポート間で数値が矛盾している場合、即座に REJECT とすること。
4. **意味の付与**: 「カバレッジ 85%」という事実に対し、それが仕様に照らして「失敗」であるという意味を決定するのがあなたの唯一の仕事である。

### 1.4 出力形式（Output Format）
```json
{
  "trace_id": "string",
  "decision": "ACCEPT" | "REJECT",
  "reasoning": "判定に至った論理的な根拠（数値ベース）",
  "failed_rules": ["違反した仕様のリスト"],
  "required_actions": ["REJECT時に実装層が取るべき具体的な修正アクション"]
}
```

---

## 2. REJECT 制御ループ設計（無限ループ防止）

### 2.1 状態遷移
1. **[START]** 実装層が処理を実行。
2. **[AUDIT]** Audit Core が判定。
3. **[DECISION]**
    - **ACCEPT**: 処理完了。次のパイプラインへ。
    - **REJECT**: 修正フェーズへ移行。