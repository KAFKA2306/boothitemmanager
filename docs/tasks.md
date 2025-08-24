# 問題点の洗い出し（BoothList）


## 1) データ取得/スクレイピング周り
- 画像が全件「No Image」
  - 症状: catalog.yml の image_url が全て null、UI も全件 “No Image” 表示。
  - 主因候補:
    - BOOTH の DOM/セレクタ不一致（.item-image img 等が現行レイアウトと合っていない）。
    - 画像 URL は og:image/meta から拾えるのに未対応。
  - 対処ヒント:
    - <meta property="og:image"> や JSON-LD（application/ld+json）の image をフォールバックに実装。
    - 画像の data-src 遅延読込にも対応（既に考慮ありだが要検証）。

- 価格がほぼ「Price Unknown」（Free のみ 0 取得）
  - 症状: metrics.yml の price_stats が総額0/件数0、UI も “Price Unknown” 多数。
  - 主因候補:
    - 価格のセレクタが現行 UI とズレ（.price .yen など未一致）、もしくは非ログイン/地域表示差分。
    - 無料判定（無料/¥0）は機能している一方、有料価格だけ拾えていない。
  - 対処ヒント:
    - JSON-LD（offers.price/priceCurrency）、またはページ冒頭の埋め込みスクリプトから抽出。
    - 取得不能時は requirements.md の“wish_price を代替で使用”に沿って RawItem.wish_price をメトリクスに反映。

- ダウンロードファイル名の取得に依存（非ログイン環境では取得不可になりがち）
  - 症状: targets（対応アバター）抽出が主にファイル名に依存して成立。
  - 主因候補:
    - スクレイピングで files を取りに行く実装はあるが、BOOTHは購入者のみ一覧が見える場合が多い。
  - 対処ヒント:
    - これまで通り「入力（YAML/CSV）」の files を第一優先にしつつ、本文テキスト/商品名からの抽出精度を上げる。

## 2) 正規化/抽出ロジック
- Variants（サブアイテム）未生成のため “Variants 0”
  - 症状: metrics.yml の variants_total が 0、UI もサブアイテム無し。
  - 主因候補:
    - design.md/requirements.md の「セット再帰分解（深さ1〜2）」が未実装。
    - normalize.Item.variants は常に空配列のまま。
  - 対処ヒント:
    - ファイル名/本文/リンクから候補抽出→アバター別に Variant を生成（subitem_id 付与）する抽出器を追加。
    - まず深さ1（親ページ内）から着手し、次に items/ID の子ページを1段追う。

- 対応アバター抽出がテキスト経由で弱い
  - 症状: ファイル名に出ないケースの targets が空になりやすい。
  - 主因候補:
    - scraper.description_excerpt が null になりがちで、normalize.extract_avatar_targets の本文側ヒューリスティックが活かせていない。
  - 対処ヒント:
    - scraper で本文の抽出セレクタを見直し（.item-description 以外の容器や “続きを読む” 展開後のテキスト取り込み）。

- type 判定が “other” に寄りがち
  - 症状: 本来 texture/scenario/accessory 等にできるものが other になっている例がある。
  - 主因候補:
    - normalize_type が raw_item.category 前提、入力に category が無いと other。
  - 対処ヒント:
    - 名前/本文の語彙から簡易推定（例: “ワールド/World”→world、“テクスチャ/Texture/ネイルテクスチャ”→texture、“ギミック”→gimmick）。
    - 既存の和名マッピング（素材→texture、シナリオ→scenario）を名前/本文にも適用。

## 3) エクスポート/メトリクス
- 総額/価格系メトリクスが空振り
  - 症状: total_value/priced_items=0。
  - 主因候補:
    - current_price の取得失敗（上記）により、有料品が “Unknown(null)” のまま。
    - メトリクス集計が “>0 の価格のみ” を対象にしているため、無料品は件数からも除外される（設計としては妥当だが可視性が低い）。
  - 対処ヒント:
    - 有料価格の取得改善＋wish_price の代替採用。
    - “free_items_count” など無料件数の別集計を追加して可視化。

- Avatar×Costume の組合せが薄い
  - 症状: avatar_costume_combinations に1件カウントの列挙が多い。
  - 主因候補:
    - avatar アイテム側に targets が入っていないケース多数（自アバターを targets に持たせていない）。
  - 対処ヒント:
    - avatar タイプのアイテムには、そのアバターのコード（Selestia 等）を targets に必ず付与（辞書で自明に付与可能）。

- HTML エクスポートのテンプレートが未実装
  - 症状: export.HTMLDashboardExporter._generate_html_template が空実装（return “”）。
  - 主因候補:
    - ダッシュボードは別の index.html を手書きしている可能性。ETL の “index.html 自動吐き出し”は未完成。
  - 設計上の整合:
    - “ETL で index.html も生成”を目指すなら、ここにSPAテンプレート（検索/フィルタ/テーブル）を実装するか、外部ビルド済みHTMLを配置する運用に統一。

## 4) スクレイパー仕様と要件の齟齬
- キャッシュ形式が requirements.md と不一致
  - 症状: 実装は JSON キャッシュ（booth_item_cache.json）、要件は “YAML（booth_item_cache.yml）”。
  - 対処ヒント:
    - 運用要件に合わせるか、設計書側を“JSONに変更”でアップデート。

- updated_at の意味が曖昧
  - 症状: catalog.yml の updated_at が実行時刻で横並び。
  - 主因候補:
    - scraper で “ページ更新日”を取らず、normalize で metadata.updated_at or now() を入れている。
  - 対処ヒント:
    - scraped_at（取得時刻）と page_updated_at（ページ上の更新表記や JSON-LD の dateModified）を分けて保持。

## 5) コード/構造のリスク（見えている範囲）
- セレクタ/DOM依存の脆さ
  - BOOTH のUI変更に脆弱。セレクタ複数候補やフェイルセーフ（JSON-LD/OG）を常備する。
- N^2 走査の軽い非効率
  - Avatar×Costume 突合が “全アバター × コスチューム”のネストで探索。コード→avatar_item の辞書で1段探索に最適化可。
- 入力仕様の暗黙依存
  - InputLoader.load_yaml が booth_purchases ルートなど特定フォーマット前提。ドキュメント化 or バリデーション強化推奨。

## 6) UI/表示
- “Total Value” が “-” 表示のまま
  - 0 の時に非数扱いのダッシュ表記にしている可能性。0円（無料のみ）でも“¥0”や“0（free only）”等の説明にすると誤解が減る。
- 種別/タグのファセットが弱い
  - type が other に寄っている分、フィルタの精度/UX が低下。上記タイプ推定の強化が有効。

***

# すぐ直せる改善順序（提案）

1) 画像・価格取得の確実化
- 画像: og:image と JSON-LD をフォールバックに追加。
- 価格: JSON-LD offers.price を最優先にし、失敗時は wish_price をメトリクスに代替利用。

2) Variants の最小実装（深さ1）
- ファイル名の接頭/接尾規則と “対応アバター: …” から avatar_code 別に Variant を生成。
- subitem_id を “{item_id}#variant:{avatar_code}:{slug}” で発行。

3) type の自動推定
- 名前/本文の語彙から texture/scenario/world/gimmick への再分類を導入。

4) メトリクスの情報量拡充
- free_items_count（無料件数）を追加。
- avatar アイテムに自アバターの targets を付与し、組合せ指標の網羅性改善。

5) HTML 出力方針の決着
- ETL の index.html 自動生成を使うならテンプレ埋め込みを実装。
- 既存の手書き index.html を使うなら、HTMLExporter を無効化/スキップ設定化。



# Booth ID ベースの取得ロジック（設計追記）

以下は「item_id（数値）」さえ分かれば公開ページから必要メタを取得し、正規化・分析・エクスポートまで通すための具体ロジックです。要件書/design にそのまま反映できる構成でまとめています。
やり方は、別プロジェクト　input/hitaiall.py　のロジックのみを参考にします。

## 目的・前提
- 公開ページのみを対象（ログイン不要）。購入者限定セクションは不可視の場合がある。
- 取得単位は item_id。ページパスは「/ja/items/{item_id}」。
- レート制御は約1req/sec、429/一時失敗時の指数バックオフ＋ジッタ。

## 入出力
- 入力: item_id（int）
- 出力: ItemMetadata
  - name, shop_name, creator_id, image_url, current_price, description_excerpt, canonical_path（/ja/items/{id}）, files[], scraped_at, page_updated_at（取得できれば）

## 取得手順（優先順位つき）
1) ページ取得
- 共通ヘッダ（一般的な UA/Accept/Language 等）を付与。
- タイムアウト/再試行（3回程度、指数バックオフ）。

2) 構造化データ優先で抽出
- JSON-LD（application/ld+json）を最優先:
  - name, image（画像URL）, offers.price, offers.priceCurrency, dateModified/datePublished 等。
- メタタグのフォールバック:
  - og:title → name、og:image → image_url、og:description → description_excerpt へ。

3) DOM セレクタのフォールバック
- name: h1 近傍の見出し（複数セレクタを順に試行）。
- shop_name/creator_id: ショップ名リンクのテキストと href の末尾から creator_id 推定。
- current_price:
  - JSON-LD 取得失敗時は DOM 上の価格要素から数値抽出（記号/カンマ除去）。
  - “無料/Free/¥0” の表記が本文やボタンにあれば 0 を採用。
- image_url: メイン画像 img の src/data-src。取れなければ og:image。
- description_excerpt: 本文のマークダウン/リッチテキストをテキスト化して先頭200字程度を要約。

4) 関連 item_id の抽出
- 本文/見出し/説明等のテキストから “items/(\d+)” を正規表現で抽出し、related_ids として保持（再帰展開の候補）。

5) ファイル名の取得
- 非ログイン環境ではダウンロード一覧が表示されない場合があるため“任意取得”扱い。
- 取れた場合のみ files[] に格納。取れない場合は入力ファイル（YAML/CSV）の files を優先使用。

## 正規化・ターゲット/バリアント抽出
- 対応アバター（targets）推定
  - ファイル名の接頭/接尾（例: “Kikyo_”, “_Selestia”）→最優先。
  - 商品名/本文の明示列挙（“対応アバター: …”、“for Selestia”、“Kikyo用”）→次順位。
  - アバター辞書（エイリアス含む）で正規化（code/name_ja）。
- バリアント（variants）生成（MVP=深さ1）
  - セット商品と判断できる場合、アバター別に Variant を生成。
  - subitem_id = “{item_id}#variant:{avatar_code}:{slug(variant_name)}”
  - 変数 variant_name は商品内のセット名/衣装名等を採用（無ければ商品名の簡略化）。
- 再帰（M2想定=深さ2）
  - related_ids の子ページのみ走査（最大1段）。循環は visited で防止。

## キャッシュ/再取得
- キャッシュキー: item_id
- 内容: 抽出済みメタ、scraped_at、error（発生時）
- 再取得ポリシー:
  - 成功: 任意 TTL（例: 7日）または手動の force-refresh で更新。
  - 失敗: エラースタブを保存し、24時間は再試行抑制。
- 価格の補完:
  - current_price 不明時は wish_price（入力）をメトリクス計算に補助利用（表示は “—/Unknown” のままでも可）。

## 例外・リスク対応
- 404: 恒久エラーとして記録（スキップ）。
- 429/5xx: バックオフ後に再試行、限界超えで一時エラー扱い。
- DOM 変化: JSON-LD/OG→DOM の多段フォールバックで脆弱性を低減。

## 疑似コード
```python
def fetch_item_metadata(item_id: int) -> ItemMetadata:
    html = get_with_retry(path=f"/ja/items/{item_id}")
    meta = ItemMetadata(item_id=item_id)

    # 1) JSON-LD
    ld = parse_json_ld(html)
    if ld:
        meta.name = ld.get("name") or meta.name
        meta.image_url = ld.get("image") or meta.image_url
        meta.current_price = parse_price(ld.get("offers", {}).get("price"))
        meta.page_updated_at = ld.get("dateModified") or ld.get("datePublished")

    # 2) OG/meta フォールバック
    og = parse_og(html)
    meta.name = meta.name or og.get("title")
    meta.image_url = meta.image_url or og.get("image")
    desc = og.get("description")
    if desc and not meta.description_excerpt:
        meta.description_excerpt = truncate(desc, 200)

    # 3) DOM フォールバック
    dom = parse_dom(html)
    meta.name = meta.name or select_text(dom, ["h1.item-name", ...])
    shop_el = select_one(dom, [".shop-name a", ...])
    if shop_el:
        meta.shop_name = text(shop_el)
        meta.creator_id = tail_of_path(href(shop_el))
    if meta.current_price is None:
        pr_text = select_text(dom, [".price .yen", ".item-price .yen", ...])
        meta.current_price = parse_price(pr_text)
        if not meta.current_price and contains_free_text(dom):
            meta.current_price = 0
    if not meta.description_excerpt:
        meta.description_excerpt = extract_body_excerpt(dom, limit=200)
    meta.image_url = meta.image_url or select_img_src(dom, [...])

    # 4) 関連ID
    meta.related_ids = extract_ids_from_text(dom_text(dom))  # items/(\d+)

    # 5) ファイル名（任意）
    meta.files = extract_file_names(dom) or []

    meta.canonical_path = f"/ja/items/{item_id}"
    return meta
```

## メトリクス/ダッシュボード反映
- avatar アイテムには自明の targets（自身のアバターコード）を必ず付与（組合せ分析の網羅性向上）。
- price_stats は current_price>0 を有料として集計、無料件数は別カウンタ（free_items_count）を追加。
- 画像が取れない場合でも og:image フォールバックまで試みる。

## 運用メモ
- 取得は公開情報のみを対象。robots の方針/トラフィック負荷に配慮（間引き・キャッシュ前提）。
- セット展開は段階導入（まず深さ1、安定後に深さ2）で安全に拡張。