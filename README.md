# BoothItemManager2

BOOTH上の公開VRChatアセット情報を収集・正規化し、検索・比較・分類できる静的ダッシュボードとオントロジー管理システムです。

## 公開先

- GitHub Pages: https://kafka2306.github.io/boothitemmanager/
- Cloudflare Pages: https://boothitemmanager.pages.dev/

## 因果・証拠オントロジー

上位システムは `MarketplaceAssetCatalogSystem` です。

```text
販売者の公開出品情報
→ 出品・販売者の同定
→ 原文フィールド保存
→ 正規化
→ 派生分類・類似度計算
→ 重複・互換性・権利状態の監査
→ 静的API・検索画面公開
```

販売者記載、マーケット観測、正規化値、派生タグ、対応アバター、ライセンス観測を別クラスとして保存します。タイトルや近接タグだけから対応アバターや利用許諾を推定しません。根拠が不足・矛盾する項目は `UNKNOWN` または `quarantine` とします。

- [プロジェクト・オントロジー](ontology/project.yaml)
- [共通因果・証拠オントロジー](https://github.com/KAFKA2306/know/blob/main/ontology/causal-evidence-core.yaml)
- [開発ガイド](AGENTS.md)
- [エージェント向け索引](llms.txt)

## 特長

- **Zero-Fat Architecture**: 公開成果物を軽量化し、配信制約を管理
- **Evolving Ontology Loop**: 出典フィールドを保持したまま正規タグを更新
- **Fail-Fast Validation**: 破損データや不整合を黙って継続しない
- **Novelty-Aware Similarity**: 新規性と多様性を考慮した類似候補

## 必要要件

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- [go-task](https://taskfile.dev/)

## 使い方

```bash
uv sync
playwright install chromium
task build
task check
task serve
```

## 主な構成

- `src/boothitemmanager2/`: 収集・正規化・検索生成
- `ontology/`: タグ・スタイル知識とプロジェクト意味モデル
- `docs/`: 仕様・ADR
- `api/` / `dist/`: 生成された静的APIとダッシュボード