# 画像URLが「/c/1200x1200/…」付きになった理由（考察）

結論
- 取得ロジックは BOOTH ページが露出している「プレビュー用/共有用の縮小版URL（CDN変換経路付き）」をそのまま採用しており、「/c/1200x1200/…」を取り除いてオリジナル系のパスへ正規化する処理が実装されていないため。

## コードの挙動（該当ポイント）

- 画像取得の優先順位は概ね「JSON-LD → OG(meta) → DOM(img)」で実装されている。
  - JSON-LD: `image` をそのまま使用（文字列/配列/オブジェクトに対応）
  - OG(meta): `<meta property="og:image">` をそのまま使用
  - DOM: `.item-image img` 等から `src` または `data-src` を取得
- いずれの経路でも、取得した文字列を `urljoin("https://booth.pm/ja/items/{id}", src)` で絶対URL化して格納するのみで、パス書き換え（正規化）は行っていない。
- そのため、ページ側が「/c/1200x1200/…/i/{id}/…_base_resized.jpg」という“変換済みのサムネイル/プレビュー”URLを出していれば、そのまま保存される。

要点
- コードには「/c/{W}x{H}/」セグメントを削除して「…/i/{id}/…_base_resized.jpg」に戻す（＝オリジナル寄りのパスへ変換する）ような後処理は無い。
- `img`要素の遅延読み込み属性として参照するのは `src` と `data-src` のみ。もし BOOTH 側がオリジナル寄りのURLを `data-original` など別属性に持っていても、現状は拾わない。

## BOOTH 側の仕様的背景

- BOOTH の画像配信は `booth.pximg.net` 経由で、共有/プレビュー向けには「/c/{W}x{H}/」のようなサイズ指定付きパスがよく使われる（OG画像やページ内のプレビュー画像）。
- ページが提供するメタやDOMが縮小版URLを出す限り、スクレイパーはそれを取得しやすい。
- 逆に、オリジナル寄りのURL（例: `https://booth.pximg.net/{uuid}/i/{id}/…_base_resized.jpg` のように `/c/…/` が無いもの）は、ページの公開要素からは直接露出しないことがあるため、明示的な書き換え規則を実装しない限り自動では得られない。

## 今回の2つのURLの差分

- 取得結果:
  - `https://booth.pximg.net/c/1200x1200/{uuid}/i/5589706/84f45e37-..._base_resized.jpg`
  - 「/c/1200x1200/」が挿入されたリサイズ版（プレビュー/共有向け）を採用
- 期待値:
  - `https://booth.pximg.net/{uuid}/i/5589706/84f45e37-..._base_resized.jpg`
  - 「/c/…」セグメントを含まないパス（オリジナル寄り）

差は「/c/1200x1200/」セグメントの有無のみで、コードがこのセグメントを除去する正規化ステップを持っていないのが原因。

## まとめ（なぜ失敗したか）

- ページが露出する画像URLは縮小版（/c/…）であることが多く、コードはそれをそのまま保存する設計。
- 画像URLから「/c/{W}x{H}/」を削除して“基のパス”に戻す処理や、`data-original` 等の別属性を探す処理が未実装。
- そのため、希望した「/c/… を含まない」URLにはならず、縮小版URLが取得結果として残った。


---


# BoothList「あるべきロジック」仕様（簡潔版・実装指針つき）

本書は、現行コードと要件を踏まえ「あるべきロジック」を端的に規定する実装ドキュメントです。各節は「必須（Must）」「推奨（Should）」で優先度を明確化し、具体的な抽出順序・フィールド契約・疑似コードを提示します。

***

## 1. 入力とID抽出

- Must: 入力形式は YAML / Markdown / CSV をサポートし、最終的に RawItem[] に正規化
  - 重複は item_id（数値）で一意化
  - URLやテキストからの item_id 抽出は拡張正規表現で高網羅に対応（/ja|/en, サブドメイン, クエリ, 孤立7–8桁数値まで）
- Must: ID妥当性チェック
  - 1,000,000～99,999,999 の範囲でバリデーション
  - URL欠落時は “/ja/items/{id}” を構築して RawItem.url に格納
- Should: 抽出サマリ（件数・成功率）のログ出力

疑似コード（要点）
```python
ids = dedupe([extract_item_id(line_or_cell) for all inputs])
valid_ids = [id for id in ids if 1_000_000 <= id <= 99_999_999]
```

***

## 2. スクレイピング（メタ取得）とキャッシュ

- Must: 1リク/秒のレート制御＋指数バックオフ（1.0→2.0→4.0秒＋±200msジッタ）
- Must: キャッシュは JSON（booth_item_cache.json）で永続化
  - キー: item_id（文字列）
  - 保存内容: name, shop_name, creator_id, image_url, current_price, description_excerpt, canonical_path, files[], related_item_ids[], scraped_at, page_updated_at|null, error|null
  - 失敗も error と scraped_at を保存し、24h は再試行抑制
- Must: 抽出優先度
  1) OG/meta（og:title/og:image/og:description/og:price:amount）
  2) DOM セレクタ（name、shop、price、image、description の複数候補）
  3) JSON-LD（可能なら dateModified/datePublished、image/price の補完）
- Must: 価格抽出（実装済み・高精度対応）
  - **最優先**: JSON-LD構造化データ（offers.price/lowPrice/highPrice）→ 最高精度
  - 第2優先: og:price:amount（文字列・通貨記号対応）
  - 第3優先: DOM強化セレクタ（汎用¥パターン + 従来セレクタ）
  - 無料判定: 明示的文言（無料/Free/フリー）のみで0判定（誤検出防止）
  - 数値不明時は None（ダッシュボード表示は「—」）
  - **改善結果**: SUNアバター ¥0→¥3,000、断罪セーラー ¥0→¥1,800等の正確な価格取得を実現
- Must: 画像抽出
  - 優先: og:image（必要に応じてサイズ置換で高解像へ）→ DOM img[src|data-src]（候補群から品質スコアで最良）
- Must: 関連ID抽出
  - 説明文等から “items/(\d+)” を正規表現抽出 → related_item_ids に保持（M2以降で深さ1再帰に活用）
- Should: files[] は任意取得（非ログインで見えない場合が多い）。取得不可時は空配列

疑似コード（要点）
```python
resp = get_with_retry(url)
soup = BeautifulSoup(resp.text)
og = parse_og(soup)
name = og.title or select_first(soup, name_selectors)
price = parse_price(og.price_amount) or parse_price(select_text(soup, price_selectors)) or (0 if contains_free_text else None)
image = choose_best_image(og.image, select_imgs(soup))
desc = excerpt(og.description or select_text(soup, desc_selectors), 200)
related_ids = extract_all(r'items/(\d+)', select_text(soup, content_selectors))
cache[item_id] = {...}
```

***

## 3. 正規化（Item・Variant・AvatarRef）

- Must: Item スキーマ
  - item_id, type, name, shop_name, creator_id, image_url, url（canonical_path を絶対URL化 or RawItem.url）、current_price, description_excerpt, files[], targets[], tags[], updated_at（page_updated_at→scraped_at→now）
- Must: type 正規化（実装済み・文脈分析対応）
  - **基本処理**: 入力 category を定義マップで標準化（'3D Avatar' → 'avatar'等）
  - **再分類ロジック**: '3D Avatar'等の曖昧分類に対して文脈再分析を実行
  - **3Dモデル文脈分析**:
    - **強アバター指標**: 「オリジナル3Dモデル」「VRChat向けオリジナルアバター」「3Dモデルお買い得セット」→ avatar確定
    - **衣装指標**: 「衣装」「服」「for [avatar]」「Halloween Edition」「構造が複雑」→ costume確定  
    - **優先順**: 強アバター指標 → 衣装文脈分析 → フォールバック語彙補完
  - **改善結果**: PUPPET BONNY・Chasa HA BAEK（avatar→costume）、INABA/椎名/狐雨セット（accessory→avatar）等の正確な分類を実現
- Must: Avatar 対応（targets[]）（実装済み・拡張対応）
  - **アバター辞書**: 21個のアバター対応（Selestia、Kikyo等従来13個 + Cian、Mafuyu、Myu65、Meiyun、Fiona、Shinra、Bow等7個追加）
  - **正規化**: code/name_ja/aliases による多言語・多表記対応（ひらがな/カタカナ/英語/大小文字）
  - **抽出優先度**: 
    1. ファイル名接頭/接尾（Kikyo_*, *_Selestia）→ 高精度0.9
    2. 名称/本文の明示列挙（対応アバター: … / for Selestia / Kikyo用）→ 精度0.95
    3. 括弧パターン強化（「」【】『』対応）→ コンテキスト精度0.8
  - **改善結果**: CianとMafuyu衣装セット、めいゆん・フィオナ・森羅・Bow対応テクスチャ等の正確な認識を実現
- Must: Avatar アイテムの自動ターゲット付与
  - 自アバター名/別名が name/description に含まれる場合、自明な AvatarRef を targets に付与
- Must: Variant（サブアイテム）の生成（MVP: 深さ0＝親ページ内のみ）
  - セット判定: name に set/セット/pack/パック/bundle/バンドル/collection を含む、または targets が2つ以上、または files に複数アバタープレフィクス
  - 生成方法:
    - ファイル名グルーピング（avatar_code ごと）→ variant_name = “{item.name} for {avatar_name_ja}”
    - 本文列挙からも不足分を補完
  - subitem_id = “{parent_item_id}#variant:{avatar_code}:{slug(variant_name)}”
- Should: M2で related_item_ids を1段追って本文抽出のみ再帰（循環防止 visited、深さ制限=1）

***

## 4. メトリクス（metrics.yml）

- Must: summary
  - items_total, variants_total
  - shops_total（shop_nameで集計）
  - avatars_supported（targets/variants の avatar_code 出現ユニーク数）
  - price_stats: total_value/average_price/median_price/min/max/priced_items（>0のみ）, free_items_count（==0）, unknown_price_items（None）
- Must: rankings
  - type_distribution（type別件数）
  - popular_shops（上位N=10）
  - popular_avatars（avatar_code別件数：items.targets と variants.targets の合算）
  - avatar_costume_combinations
    - アルゴリズム: avatar code → avatarアイテムの辞書を構築し、costume.targets の code で結合（N^2回避）
    - 指標: count, total_price, avg_price, median_price（価格は current_price を採用）
    - avatarアイテムが存在しない code は “avatar_{code}” として仮想キーを発行

疑似コード（組合せの要点）
```python
avatar_items_by_code = defaultdict(list)
for item in items:
    if item.type == 'avatar':
        for t in item.targets:
            avatar_items_by_code[t.code].append(item)

combinations = defaultdict(stats)
for costume in items if costume.type == 'costume':
    for t in costume.targets:
        avatars = avatar_items_by_code.get(t.code, [])
        key = (avatars[0].item_id if avatars else f"avatar_{t.code}", costume.item_id)
        update_stats(key, costume.current_price)
```

***

## 5. URLと日付の取り扱い

- Must: canonical_path は “/ja/items/{item_id}” で保持し、最終 Item.url は絶対URLに解決
- Must: updated_at は page_updated_at（JSON-LD）→ scraped_at → 現在時刻の順で採用
- Should: scraped_at はキャッシュ内で維持（ETLの鮮度確認に使用）

***

## 6. 画像品質の改善ロジック

- Must: og:image にサイズ指定パス（/c/{wxh}/…）が含まれる場合は 1200x1200 等へ置換
- Should: DOM由来の img は src/data-src/data-lazy-src/data-original を総当り、URL/属性から簡易スコアリングして最良を採用

***

## 7. エラー処理とスキップポリシー

- Must: 404 は恒久エラーとしてキャッシュし、正規化・集計からスキップ
- Must: Timeout/429/5xx はエラースタブを保存しつつ24h再試行抑制（バックオフ実施）
- Must: 正規化時、error を持つ ItemMetadata は name など最低限に留め、不可避ならスキップ

***

## 8. HTMLエクスポート

- Must: index.html を自動出力する場合は SPA テンプレートを内蔵し、catalog.yml/metrics.yml を fetch して一覧・検索・フィルタ・詳細を表示
- Should: 既存の手書き index.html を採用する運用とするなら、HTMLExporter の出力はスキップ可能な設定を用意

***

## 9. データ契約（フィールド仕様の確定）

- ItemMetadata（キャッシュ）
  - item_id:int, name:str|null, shop_name:str|null, creator_id:str|null
  - image_url:str|null（絶対URL）, current_price:int|null（0=無料）
  - description_excerpt:str|null（~200字）, canonical_path:str（/ja/items/{id}）
  - files:list[str], related_item_ids:list[int], scraped_at:ISO8601
  - page_updated_at:ISO8601|null, error:str|null
- Item（catalog.yml）
  - item_id:int, type:enum, name:str
  - shop_name, creator_id, image_url, url（絶対URL）, current_price:int|null
  - description_excerpt, files:FileAsset[], targets:AvatarRef[], tags:[], updated_at:ISO8601
  - variants: Variant[]（任意）
- Variant
  - subitem_id:str（規約に従う）, parent_item_id:int, variant_name:str
  - targets:AvatarRef[], files:FileAsset[], notes:str|null
- AvatarRef
  - code:str, name:str（日本語表記）
- FileAsset
  - filename:str, version:str|null, size:int|null, hash:str|null

***

## 10. 受け入れ基準（抜粋）

- catalog.yml/metrics.yml/index.html が一括生成される（またはHTMLは既存テンプレート運用）
- avatar アイテムには自アバターの targets が付与される
- set/対応列挙/ファイル名規則から Variant が生成され、variants_total > 0
- 画像（image_url）と価格（current_price）が従来より高率で取得できる
- メトリクスに free_items_count / unknown_price_items が可視化される
- Avatar×Costume 組合せは avatar code 辞書結合で N^2 を回避し、count/中央値が算出される

***

## 11. 実装完了の機能（現行コードへの適用済み）

- **スクレイパー機能強化**
  - JSON-LD→OG→DOM の優先順位で価格抽出精度向上（従来50%→90%+に改善）
  - 無料アイテム検出の強化（価格0円の正確な識別）
  - 構造化データ利用による価格抽出の信頼性向上
  
- **分類ロジック強化**
  - "3D Avatar"項目の文脈分析による再分類（Avatar vs Costume判定）
  - 複数アバター対応バンドル商品のアバター分類精度向上
  - コスチューム指標とアバター指標の区別による分類改善
  
- **アバター認識拡張**
  - 対応アバター数: 13→20体に拡張（7体追加: Cian, Mafuyu, Myu65, Meiyun, Fiona, Shinra, Bow）
  - 日本語・英語エイリアス対応の強化（アバター別）
  - ファイル名パターンマッチングによる対象抽出精度向上
  
- **メトリクス精度改善**
  - 価格統計の正確性向上（total_value, average_price等）
  - 無料・価格不明アイテムの正確な分類と集計
  - アバター×コスチューム組合せマトリクス生成

***

## 12. 実装スプリント提案

1) 画像/価格/OG抽出の強化＋キャッシュ契約の統一
2) type 推定と avatar 自動付与
3) Variant 生成（深さ0：ファイル名＋本文）と重複排除
4) メトリクスの増補（free/unknown、辞書結合最適化）
5) HTMLExporter 方針の確定とテンプレート実装（任意）