# Static Data API v1

BoothItemManager2 は、既存の `api/catalog_summary_part*.json` を後方互換の正準配布データとして維持しつつ、クライアントが全 shard を総当たりせず安全に同期・検索準備できる制御用 API を `/api/v1/` に生成します。

## エンドポイント

- `/api/v1/manifest.json` — 全体件数、shard件数、各配布物と元shardの byte 数・SHA-256
- `/api/v1/shards.json` — shard連番、相対URL、件数、byte数、SHA-256
- `/api/v1/facets.json` — 既存レコードに明示された category / shop / status / avatar の集計
- `/api/v1/schema-profile.json` — フィールドの出現件数・出現率・JSON型の実測プロファイル

既存の `api/catalog_summary_part*.json` は削除・改名しません。

## 差分同期

まず `manifest.json` だけを取得し、`source_shards[].sha256` を前回値と比較してください。SHA-256 が変化した shard だけ再取得できます。

```python
import hashlib
import json
from urllib.request import urlopen

base = "https://boothitemmanager.pages.dev/api/v1"
manifest = json.load(urlopen(f"{base}/manifest.json"))
print(manifest["record_count"], manifest["shard_count"])
```

各 shard の完全性は次のように検証できます。

```python
payload = urlopen("https://boothitemmanager.pages.dev/api/catalog_summary_part1.json").read()
print(hashlib.sha256(payload).hexdigest())
```

期待値は `manifest.json` の `source_shards[].sha256` を利用します。

## 欠損値

- stable ID がないレコードは削除せず、`manifest.json` の `records_without_stable_id` に件数を記録します。
- facet候補フィールドが存在しない場合は推測せず、そのfacetには追加しません。
- schema profile は観測されたJSON型だけを記録し、型変換や補完を行いません。

## 更新・履歴

`catalog_summary_part*.json` の既存生成パイプラインを変更せず、その時点の配布shardから v1 を決定的に再生成します。通常CIとCloudflare PagesビルドはBOOTHへの外部アクセスを行いません。これにより、配布確認のためだけにBOOTHへ反復アクセスすることを避けます。

## 出典・権利・利用条件

元データはBOOTH上でショップオーナーが公開している出品情報を既存収集処理が観測したものです。本プロジェクトはBOOTHまたはピクシブ株式会社の公式サービスではありません。商品画像・名称・説明文その他の権利は各権利者に帰属し、価格・在庫・説明・利用条件は必ず販売ページの最新表示を優先してください。

BOOTHはピクシブ株式会社が運営しています。2026年6月22日にピクシブ株式会社のサービス共通利用規約が改定され、BOOTHを含む同社サービスに適用されています。運用時は最新のサービス共通利用規約およびBOOTHガイドラインを確認してください。

- BOOTH: https://booth.pm/
- BOOTHガイドライン: https://booth.pm/guidelines
- ピクシブ株式会社ポリシー: https://policies.pixiv.net/
- 2026-06-22 規約改定告知: https://booth.pm/announcements/949

## バージョニング

`/api/v1/` では既存キーを破壊的に削除しません。破壊的変更が必要な場合は `/api/v2/` を新設します。facetやschema profileへの追加は後方互換の拡張として扱います。
