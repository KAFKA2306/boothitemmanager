# ADR-0002: Evolving Ontology Loop (EOL) と Crash-Driven な自律ガバナンス

## 📅 日付
2026-06-11

## 📝 コンテキスト（背景だよぉ！）
前回のアップデートでオントロジー v2 を導入したけど、まだ「手動メンテナンス」の限界があったんだよぉ。
1.  **静的な知識の限界**: 新しいアバターやタグが毎日生まれる BOOTH のスピードに、人間が yaml を書くだけじゃ追いつけないよ！
2.  **ハルシネーションの恐怖**: AIが勝手にデータをいじって「なんとなく動く」状態になると、データの信頼性が崩壊しちゃうの。


## 💡 決定事項（こうしたよぉ！✨）

### 1. Evolving Ontology Loop (EOL) の起動
データ自身が「自ら進化する」サイクルを組み込んだよ！
-   **Knowledge Fragmentation**: 巨大だった `aliases.yml` を `ontology/` ディレクトリに分解して、`avatars.yaml`, `tags.yaml`, `styles.yaml` として再定義。自動化パイプラインが触りやすい構造にしたんだよ🍭
-   **Evolution Pipeline**: `evolution_pipeline.py` を実装。「発見 → 検証 → 進化 → 伝播」のループを自動で回せるようにしたの✨

### 2. Crash-Driven Development (CDD) の徹底
「聖典（スタックトレース）」を信じ、AIの甘えを許さないストイックな規律を導入したよ！
-   **No try-catch**: ビジネスロジックでのエラー隠蔽を禁止。データの 0.1% でもスキーマに違反していたら、即座にプロセスを派手にクラッシュさせるようにしたよ🍭💥
-   **Formal Schema Enforcement**: `schema.json` を全アイテムの「憲法」として定義。毎回のパイプライン実行時に、4万件すべての整合性を jsonschema で厳格にチェックするよ！