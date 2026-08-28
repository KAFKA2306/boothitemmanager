https://kafka2306.github.io/boothitemmanager/

# BoothItemManager2

[![Build, Test and Deploy](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/pages.yml/badge.svg)](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/pages.yml)
[![Static API integrity](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/static-api-integrity.yml/badge.svg)](https://github.com/KAFKA2306/boothitemmanager/actions/workflows/static-api-integrity.yml)

**BOOTHで欲しい衣装を見つけても、「自分のアバターで使えるか」は商品タイトルだけでは分からない。**

対応アバター、価格、利用条件、カテゴリは販売者ごとに書き方が違います。派生タグや商品名から互換性・許諾を推測すると、販売者が一度も明示していないことまで「対応済み」に見えてしまいます。

BoothItemManager2 は、VRChat向けBOOTH商品を **販売者が明示した事実と、システムが導出した検索情報を分けたまま探し・比較する** 静的dashboardです。

- GitHub Pages: https://kafka2306.github.io/boothitemmanager/
- AI tools evidence index: https://kafka2306.github.io/boothitemmanager/ai-tools.html

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
