# BoothItemManager2

**BOOTHで欲しい衣装を見つけても、「自分のアバターで使えるか」まで同じ書き方では分からない。**

対応アバター、価格、利用条件、カテゴリは販売者ごとに表記が違います。商品タイトルや自動生成タグだけを見て互換性や許諾を決めると、販売者が明示していないことまで事実として扱ってしまいます。

BoothItemManager2は、BOOTH上で公開されているVRChat向けアセット情報を、販売者の記載とシステムの派生情報を分けたまま検索・比較できる静的ダッシュボードです。その意味を示した後で、正規化、類似度、AEO、GEOなどの技術を使います。

READMEの入口は [`KAFKA2306/articles#34`](https://github.com/KAFKA2306/articles/issues/34) の「広い問題 → 具体例 → 技術」の編集原則を維持します。対応アバターや利用許諾をタイトルや派生タグから推測せず、根拠不足は `UNKNOWN` / `quarantine` として扱います。

**GitHub Pages:** https://kafka2306.github.io/boothitemmanager/

**Cloudflare Pages:** https://boothitemmanager.pages.dev/

**AI関連ツール証拠リンク集:** https://boothitemmanager.pages.dev/ai-tools.html

## 主な機能

- 公開商品情報の収集と正規化
- 商品名、販売者、カテゴリ、価格、対応アバターなどの検索
- タグ、色、スタイル、機能による絞り込み
- 人気度に応じたフィルター順序
- 商品詳細と販売者ページへの移動
- 商品間の類似度・新規性の計算
- 対応アバター名の正規化
- 重複、根拠不足、分類矛盾の監査
- 販売ページの明示情報に基づくAI関連ツール候補の抽出
- 大規模データを分割した静的API生成
- AEO / GEO向け構造化情報と検索エンジン監査

## AI関連ツール候補の扱い

AI関連候補は、販売者が商品名・説明・タグで明示した肯定的な証拠だけを使います。

- `AI_TOOL`: AIアシスタントなど、商品自体がAI機能を提供
- `AI_SERVICE_INTEGRATION`: ChatGPT、Gemini、GPTなどのサービス・モデル連携
- `AI_GENERATED_COMPONENTS`: 販売者がAI生成物の含有を開示
- `AI_ASSISTED_CREATION`: 販売者がAI支援での作成・開発を開示

「AI学習禁止」という規約文だけの商品や、「自動生成」という通常の自動化だけの商品は候補にしません。ショップ内に候補商品があっても、同じショップの衣装・アバター・素材へ判定を伝播させません。

## データ処理の流れ

```text
販売者が公開した出品情報
  → 商品・販売者を同定
  → 原文フィールドを保存
  → 表記・カテゴリ・タグを正規化
  → 類似度・新規性・AI関連の明示証拠を計算
  → 重複・互換性・権利状態を監査
  → 静的APIと検索画面を生成
  → GitHub Pages / Cloudflare Pagesへ公開
```

## 情報の区分

- 販売者が記載した事実
- BOOTH上で観測した価格・評価・公開日時
- 正規化したカテゴリ・色・スタイル
- システムが生成した派生タグ
- 対応アバターの明示的な記載
- ライセンス・利用条件の観測
- 類似度・新規性などの計算値

根拠が不足または矛盾する項目は、推測で埋めず`UNKNOWN`または`quarantine`として扱います。

## 設計上の特徴

### Zero-Fat Architecture

生成物を必要最小限に保ち、Cloudflare Pagesなどのファイル数・サイズ制約に対応します。大きな検索インデックスや詳細データは分割して配信します。

### Evolving Ontology Loop

元の出品情報を保持したまま、正規タグ、カテゴリ、スタイル語彙を監査・更新します。低品質な数値タグ、汎用語、誤ったアバター名を自動的に正規語彙へ昇格させません。

### Fail-Fast Validation

破損JSON、欠損フィールド、カテゴリ不整合、配信制約超過を検知した場合、黙って不完全なサイトを公開しません。

### Novelty-Aware Similarity

単に似た商品を並べるだけでなく、同質な候補の集中を抑え、多様性と新規性を考慮します。

## 必要環境

- Python 3.12以上
- `uv`
- `go-task`
- Playwright Chromium

## ローカル実行

```bash
uv sync
playwright install chromium
task build
task check
task serve
```

## 主な構成

```text
src/boothitemmanager2/  収集・正規化・検索データ生成
ontology/               タグ・スタイル語彙と意味モデル
docs/                   仕様・ADR・監査記録
api/                    生成された静的API
dist/                   公開ダッシュボード
AGENTS.md                開発・監査ルール
llms.txt                 エージェント向け入口
```

機械可読な定義:

- [プロジェクト・オントロジー](ontology/project.yaml)
- [共通因果・証拠オントロジー](https://github.com/KAFKA2306/know/blob/main/ontology/causal-evidence-core.yaml)
- [開発ガイド](AGENTS.md)
- [エージェント向け索引](llms.txt)

## 注意

- 本プロジェクトはBOOTH公式または各販売者によるものではありません
- 商品価格、在庫、説明、利用規約は販売ページの最新情報を優先してください
- 対応アバターや改変可否を、派生タグだけで判断しないでください
- AI関連候補は販売ページの明示情報の索引であり、他商品の制作方法を断定しません
- 商品画像、名称、説明文などの権利は各権利者に帰属します

**README最終監査:** 2026-08-13
