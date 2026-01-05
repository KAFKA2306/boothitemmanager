# BoothList

BOOTHの購入データを収集・整理し、検索・分析・可視化できる静的ダッシュボードを生成するツール。

## 特長
- メタ取得（商品名、ショップ、画像、現在価格、URL）
- 商品の正規化と集計
- 高速フィルタと検索
- 静的出力（GitHub Pages等で配布可能）

## 使い方
1. `config.yaml` を設定
2. `python3 -m boothlist.main` を実行
3. `dist/index.html` を確認