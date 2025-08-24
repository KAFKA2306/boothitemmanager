# Booth ID ベースの取得ロジック（設計追記）

以下は「item_id（数値）」があれば公開ページから必要メタを取得し、正規化・分析・エクスポートまで通すための実装指針。

## 目的・前提
- 対象は公開ページのみ。
- 取得単位は item_id、ページは /ja/items/{item_id}。
- キャッシュはJSON（item_idキー）で永続化。成功・失敗ともに保存して無駄な再訪を抑制。

## 入出力
- 入力: item_id: int
- 出力: ItemMetadata
  - item_id: int
  - name: str|null
  - shop_name: str|null
  - creator_id: str|null（shopサブドメイン等から推定）
  - image_url: str|null（絶対URL）
  - current_price: int|null（JPY。無料は0）
  - description_excerpt: str|null（先頭200字程度）
  - canonical_path: str（/ja/items/{item_id}）
  - files: list[str]（取れた場合のみ）
  - scraped_at: datetime ISO8601（取得時刻）
  - page_updated_at: datetime ISO8601|null（取れた場合のみ）
  - error: str|null（失敗時の簡易理由）

## 取得手順（優先順位つき）
1) ページ取得
- リクエストヘッダ（例）
  - User-Agent: 一般的なChrome系UA
  - Accept-Language: ja,en-US;q=0.9,en;q=0.8
- タイムアウト設定＋最大3回リトライ（1.0s→2.0s→4.0s＋±200msジッタ）。各試行前に最小1秒待機（全体でも約1req/secを担保）。
- ステータス200以外は error を格納してキャッシュし、早期リターン。

2) 構造化/メタからの抽出（取得できるものを使う）
- まずはメタタグ（OG等）を優先（hitaiall相当）:
  - og:title → name
  - og:image → image_url
  - og:description → description_excerpt
  - og:price:amount → current_price（数値化）
- JSON-LDがある場合は補完として利用可（将来拡張）:
  - name, image, offers.price, dateModified/datePublished → page_updated_at 候補
- どちらも欠落ならDOMにフォールバック。

3) DOM セレクタのフォールバック（複数候補を順に試行）
- name:
  - h1.item-name, h1.u-tpg-title1, h1[itemprop="name"]
  - 取得不可なら og:title を再参照
- shop_name:
  - a.shop-name, div.u-text-ellipsis > a, a[itemprop="author"], og:site_name
- creator_id 推定:
  - ページ内リンクの href から "https://{sub}.booth.pm" の {sub} を抽出
  - 次点で "/shop/{creator}" パターン
  - 最後にレスポンスURLのサブドメインを推定
- current_price:
  - div.price, span[itemprop="price"], og:price:amount
  - 正規表現で ¥やカンマを除去して整数化（例: r'¥\s*([\d,]+)'）
  - “無料|Free|¥0” 文言が主要要素にあれば 0 を採用
- image_url:
  - img.market-item-detail-item-image, img[itemprop="image"] の src または data-src
  - 取れなければ og:image
  - 相対URLは絶対化（ベースは /ja/items/{item_id}）
- description_excerpt:
  - 説明領域のテキスト化→先頭200字に整形（改行・余分な空白を圧縮）
- page_updated_at:
  - JSON-LDの dateModified/datePublished があればISO8601正規化（なければnull）

4) 関連 item_id の抽出（再帰候補）
- ページ本文/説明のテキストから r'items/(\d+)' で抽出。
- 設計上は related_ids として保持（MVPでは格納のみ、展開は深さ1以降で検討）。

5) ファイル名の取得（任意）
- 非ログイン環境ではDL一覧が出ないことが多いので“任意取得”扱い。
- 表示されていればファイル名テキストを files[] に格納。
- 取れない場合は入力データ（YAML/CSV等）の files を優先採用。

## キャッシュとエラー処理
- キー: str(item_id)。値: 上記ItemMetadata相当の辞書。
- 成功・失敗ともに scraped_at を付与して保存。
- 一時的な失敗（Timeout/429等）も error つきで保存し、頻回再試行を抑制（例: 次回は一定時間後のみ再試行）。
- 404は恒久エラー扱いで記録（正規化・集計ではスキップ）。

## 正規化とのインターフェース
- canonical_path は常に /ja/items/{item_id} を格納（URL文字列ではなくパス）。
- image_url は絶対URLで出力。
- current_price は int|null。無料は 0、判定不能は null。
- description_excerpt は200字程度に丸め済み。
- files は存在時のみ。なければ空配列。

## 実装スケッチ（擬似コード）
```python
def fetch_item_metadata(item_id: int, cache: dict) -> ItemMetadata:
    if str(item_id) in cache:
        return cache[str(item_id)]

    url = f"https://booth.pm/ja/items/{item_id}"
    headers = {
        "User-Agent": UA_CHROME,
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    resp = get_with_retry(url, headers=headers, timeout=30)  # 1req/sec + backoff
    if not resp.ok:
        meta = stub_error(item_id, f"HTTP {resp.status_code}")
        return save_cache(cache, item_id, meta)

    soup = BeautifulSoup(resp.text, "html.parser")
    meta = ItemMetadata(
        item_id=item_id,
        name=pick_name(soup),                    # og:title → h1...
        shop_name=pick_shop_name(soup),         # a.shop-name → ...
        creator_id=pick_creator_id(soup, resp), # {sub}.booth.pm
        image_url=pick_image(soup, base=url),   # img[src|data-src] → og:image
        current_price=pick_price(soup),         # div.price → og:price:amount → 0 if free
        description_excerpt=pick_excerpt(soup), # 先頭200字
        canonical_path=f"/ja/items/{item_id}",
        files=pick_files_optional(soup),        # 任意
        page_updated_at=pick_updated_at_optional(soup), # JSON-LD等（任意）
        scraped_at=now_iso(),
        error=None
    )

    return save_cache(cache, item_id, meta)
```

## テスト観点
- 日本語/英語混在ページでの name/shop/price 抽出の頑健性（複数セレクタ順）。
- 価格の数値化（¥/カンマ/空白の除去、無料判定）。
- 画像の取得（data-src/相対URL絶対化、og:imageフォールバック）。
- クリエイターID推定（サブドメイン/パス両対応）。
- 一時失敗時の指数バックオフ＋キャッシュ抑制が機能すること。
- 404/非公開時に error スタブで下流（正規化/集計）を破綻させないこと。

以上を requirements.md / design.md の「メタ取得」「スクレイピング」「エラー/キャッシュ」節に追記すれば、そのままMVP～M2の実装方針として整合が取れます。