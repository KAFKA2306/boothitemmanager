# ADR 0006: VRCFinder互換のカテゴリプロパティによるオントロジー定義の最適化 🌸

## ステータス (Status)
**承認済み (Accepted)** ✨

## 背景 (Context) 🎀
これまでのBoothItemManager2のオントロジー定義スキーマ（`ontology/schema.json`）には、`style` 以外の細分化された分類タグ（`outfit_type` や `accessory` など）を格納するためのフィールド定義が「不足」していました！
VRCFinder等の外部市場データと当データベースのタグ品質を比較した際、カテゴリ定義と公開用インデックスとの間で不整合が発生しやすくなっていることが判明しました。

## 決定事項 (Decisions) 🍭
データの整合性を担保し、VRCFinderとのシームレスな同期を実現するために、以下の「大改造」を行いました！
1. **`schema.json` の拡張:**
   - 以下のVRCFinder対応プロパティを `properties` に追加しました：
     - `outfit_type`, `appearance`, `color`, `accessory`, `body_type`, `feature`, `platform`, `season`
2. **インデックスジェネレータの対応:**
   - [search_builder.py](file:///home/kafka/projects/boothitemmanager/src/boothitemmanager2/agents/search_builder.py) と [api_generator.py](file:///home/kafka/projects/boothitemmanager/src/boothitemmanager2/agents/api_generator.py) を修正し、生成するAPIインデックス（`search_index.json` や catalog_summary等）に上記プロパティが正しく格納・シリアライズされるようにしました。
3. **エボリューションループによる同期:**
   - [evolve_ontology.py](file:///home/kafka/projects/boothitemmanager/scripts/evolve_ontology.py) を実行し、オントロジー（[tags.yaml](file:///home/kafka/projects/boothitemmanager/ontology/tags.yaml) / [styles.yaml](file:///home/kafka/projects/boothitemmanager/ontology/styles.yaml)）の定義をVRCFinderの統計データに基づいて再定義・拡張しました！

## 帰結 (Consequences) 🌟
- **データ品質の向上:** 分類プロパティがすべて揃い、バリデーションと検索の両面で正確性が大幅に向上しました！✨
- **Zero-Trust Validation:** [evolution_pipeline.py](file:///home/kafka/projects/boothitemmanager/evolution_pipeline.py) による自動バリデーションが全てのプロパティで問題なく通るようになり、データの一貫性が完全に保障されました！
- **VRCFinderとの同期確立:** 今後のタグ拡張も同じオントロジースキーマ上でスムーズに行えるようになりました 🍬

---
これでオントロジーの整合性はバッチリです！やったね！✨🍵
