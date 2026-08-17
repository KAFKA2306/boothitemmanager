# BoothItemManager2

[![Build, Test and Deploy](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/pages.yml/badge.svg)](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/pages.yml)
[![Static API integrity](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/static-api-integrity.yml/badge.svg)](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/static-api-integrity.yml)
[![Agent Verification Harness](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/agent_verification.yml/badge.svg)](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/agent_verification.yml)

**BOOTHで欲しい衣装を見つけても、「自分のアバターで使えるか」は商品タイトルだけでは分からない。**

対応アバター、価格、利用条件、カテゴリは販売者ごとに書き方が違います。派生タグや商品名から互換性・許諾を推測すると、販売者が一度も明示していないことまで「対応済み」に見えてしまいます。

BoothItemManager2 は、VRChat向けBOOTH商品を **販売者が明示した事実と、システムが導出した検索情報を分けたまま探し・比較する** 静的dashboardです。

- Cloudflare Pages: https://boothitemmanager.pages.dev/
- GitHub Pages: https://kafka2306.github.io/boothitemmanager/
- AI tools evidence index: https://boothitemmanager.pages.dev/ai-tools.html

## Vision

「気になる商品を見つける」から、**買う前に“自分に使える根拠があるか”まで確認できる商品探索**へ変えます。

利用者が判断したいこと:

- 自分のavatarへの対応が販売ページに明示されているか
- 価格・カテゴリ・販売者を比較できるか
- 似た商品だけでなく別の選択肢も見つかるか
- 利用条件をどこまで確認できたか
- AI関連という分類は販売者自身の説明に基づくか
- 根拠不足ならUNKNOWNとして見分けられるか

## Design philosophy

- **Seller evidence before inference.** 対応avatar・利用条件・AI関連性をtitleや派生tagだけで確定しない。
- **Observed and derived stay separate.** 販売者記載、BOOTH観測値、正規化tag、similarity scoreを別種の情報として保持する。
- **Unknown is safer than confident fiction.** 根拠不足・矛盾は`UNKNOWN` / `quarantine`へ送る。
- **No shop-wide propagation.** 1商品がAI関連でも、同一shopの他商品へ判定を伝播しない。
- **Diversity matters.** similarityだけで同質候補を並べず、noveltyを使って探索幅を残す。
- **Static distribution must stay bounded.** Pagesのfile/size制約を超えないよう大規模dataを分割し、壊れたartifactをpublishしない。
- **Latest seller page wins.** dashboardは発見・比較を助けるが、価格・在庫・規約の最終確認は販売ページで行う。

## Why / 差別化

一般的な商品検索は「キーワードが一致するか」「似ているか」を中心にします。BoothItemManager2 は、**検索結果の横に“何が観測事実で、何が派生情報で、何がまだ分からないか”を残すこと**を中心にします。

AEO / GEO、ontology、similarity、static APIは価値そのものではありません。これらは、販売者が書いていない互換性や制作方法をシステムが勝手に事実化しないための手段です。

## User journey

```text
欲しいカテゴリ / avatar / styleを探す
  → 候補を絞る
  → seller-stated compatibilityを見る
  → derived tags / similarityを補助情報として使う
  → UNKNOWN / conflictを確認する
  → BOOTH商品ページへ移動
  → 最新価格・規約・対応条件を最終確認
```

## What you can do

- 商品名 / 販売者 / カテゴリ / 価格で検索
- 明示対応avatarで絞り込み
- tag / color / style / featureで探索
- 人気度に応じたfilter ordering
- 類似度 + noveltyで関連商品探索
- duplicate / evidence gap / classification conflict監査
- seller evidenceに基づくAI-related tool候補抽出
- static API再利用
- AEO / GEO向け構造化情報生成

## Evidence model

```text
seller public listing
  → observed fields
  → normalization
  → derived category / tag / similarity
  → compatibility / license evidence audit
  → UNKNOWN / quarantine / publishable
  → static API / search UI
```

情報種別:

- seller-stated fact
- BOOTH observed value
- normalized vocabulary
- derived tag
- explicit avatar compatibility
- observed license/usage condition
- calculated similarity / novelty

これらを一つの「商品属性」へ潰しません。

## AI-related tool evidence

AI-related候補は肯定的なseller evidenceがある場合だけ付与します。

- `AI_TOOL`
- `AI_SERVICE_INTEGRATION`
- `AI_GENERATED_COMPONENTS`
- `AI_ASSISTED_CREATION`

`AI学習禁止`という規約だけ、通常の`自動生成`という語だけではAI関連商品と判定しません。

shop内の1商品から他商品へ判定を伝播しません。

## Evolving ontology

元listingを保持したまま、category / style / avatar / tag vocabularyを改善します。

- 数字だけの低品質tag
- 汎用語
- 誤ったavatar名
- seller evidenceのない互換性

をcanonical vocabularyへ自動昇格しません。

## Distribution / Zero-Fat boundary

大規模datasetをPages制約へ収めるため、検索index・詳細data・APIを必要な単位へ分割します。

fail-fastする代表例:

- broken JSON
- required field欠損
- category contradiction
- distribution size/file limit違反
- evidence contract違反

不完全なsiteを「buildできた」だけで公開しません。

## Quick start

必要環境:

- Python 3.12+
- `uv`
- `go-task`
- Playwright Chromium

```bash
uv sync
playwright install chromium
task build
task check
task serve
```

## Repository map

```text
src/boothitemmanager2/  collect / normalize / build
ontology/               controlled vocabulary / semantics
docs/                   specs / ADR / audit
api/                    generated static API
dist/                   public dashboard
AGENTS.md                agent/development contract
llms.txt                 agent-facing index
```

Machine-readable contracts:

- [Project ontology](ontology/project.yaml)
- [Causal/evidence core](https://github.com/KAFKA2306/know/blob/main/ontology/causal-evidence-core.yaml)
- [AGENTS.md](AGENTS.md)
- [llms.txt](llms.txt)

## Limits

- BOOTH公式projectではない
- price / stock / description / termsは変更される
- seller pageの最新情報を優先する
- derived tagだけでavatar compatibilityや改変可否を判断しない
- AI candidate indexはseller-stated evidenceの索引であり、他商品の制作方法を断定しない
- 商品画像・名称・説明等の権利は各権利者に帰属する

## Done

成功指標は収録商品数やtag数ではありません。

**利用者が気になる商品を見つけたあと、購入前に「何が販売者の明示情報で、何がシステムの補助推定で、何がまだ不明か」を区別して判断できること**をDoneとします。