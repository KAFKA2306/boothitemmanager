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
