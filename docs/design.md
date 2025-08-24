# BoothList MVP 設計書（design.md）

## 1. 目的（ゴール）
- BOOTHの購入資産を「検索・整理・可視化」できる最小構成を短期で実装する。
- 衣装のフルセット等を対象アバター単位に“再帰分解”し、仮想サブアイテムとして扱えるようにする。
- 正規化カタログ（catalog.yml）と基本集計（metrics.yml）を生成し、静的SPAで閲覧可能にする。

## 2. スコープ（MVPで提供）
- 入力: 購入一覧のテキスト/CSV/YAML（.input/* → 正規化）
- メタ取得: BOOTH商品ページの公開情報からのスクレイピング＋単層キャッシュ（YAML）
- セット分解: ファイル名・本文テキスト・商品内リンクのヒューリスティクス（再帰は深さ1）
- 正規化: Item/Variant/Avatar/FileAsset への分割、エイリアス統合
- 集計: 件数・合計・平均・中央値（Avatar×Costume 組合せ含む）
- 出力: catalog.yml, metrics.yml, index.html（静的SPA）

## 3. 非対象（MVPで扱わない）
- 複合ランキングスコア（unique_users/recency/compatibility の合成）
- サーバ側ファジー検索（クライアントの簡易検索で代替）
- マルチレベルキャッシュやTTL鮮度管理
- Zip内ディレクトリ階層の解析
- 関係グラフ（親子・シリーズ）の可視化
- ログインAPIや購入価格の厳密復元（現在価格または任意の希望価格で代替）

## 4. 入出力定義
- 入力ソース
  - .input/ のテキスト・CSV・YAML（URL、タイトル、タイプ、備考、希望価格など任意）
  - URLから item_id を抽出できない行はスキップ
- 出力成果物
  - catalog.yml（正規化カタログ）
  - metrics.yml（基本集計）
  - index.html（静的SPA、クライアント検索・フィルタ）

## 5. データモデル（YAML想定）

- Item
  - item_id: number
  - type: "avatar" | "costume" | "accessory" | "tool" | "gimmick" | "world" | "texture" | "scenario" | "bundle" | "other"
  - name, shop_name, creator_id, image_url, url
  - current_price: number|null
  - description_excerpt: string|null
  - files: FileAsset[]
  - targets: AvatarRef[]（例: [{code:"Selestia", name:"セレスティア"}]）
  - tags: string[]
  - updated_at: datetime
- Variant（仮想サブアイテム）
  - subitem_id: "{parent_item_id}#variant:{avatar_code}:{slug}"
  - parent_item_id: number
  - variant_name: string
  - targets: AvatarRef[]
  - files: FileAsset[]
  - notes: string|null
- Avatar
  - code: string（正規化キー）
  - name_ja: string
  - aliases: string[]
- FileAsset
  - filename: string
  - version: string|null
  - size: number|null
  - hash: string|null（任意）
- PurchaseRecord（任意）
  - timestamp: datetime
  - avatar_item_id: number|null
  - costume_item_id: number|null
  - wish_price: number|null

### 例: catalog.yml（抜粋）

```yaml
items:
  - item_id: 5589706
    type: costume
    name: "Marshmallow Full set"
    shop_name: "cherry neru"
    url: "https://booth.pm/ja/items/5589706"
    current_price: 3000
    files:
      - filename: "Kikyo_Marshmallow_Ver1.00.zip"
      - filename: "Selestia_Marshmallow_Ver1.00.zip"
    targets: []
    variants:
      - subitem_id: "5589706#variant:Kikyo:marshmallow"
        parent_item_id: 5589706
        variant_name: "Marshmallow"
        targets: [{code: "Kikyo", name: "桔梗"}]
        files:
          - filename: "Kikyo_Marshmallow_Ver1.00.zip"
      - subitem_id: "5589706#variant:Selestia:marshmallow"
        parent_item_id: 5589706
        variant_name: "Marshmallow"
        targets: [{code: "Selestia", name: "セレスティア"}]
        files:
          - filename: "Selestia_Marshmallow_Ver1.00.zip"
```

### 例: metrics.yml（抜粋）

```yaml
summary:
  items_total: 123
  variants_total: 256
rankings:
  avatar_costume_combinations:
    - avatar_item_id: 4035411
      costume_item_id: 6618690
      count: 4
      total_price: 18000
      avg_price: 4500
      median_price: 4500
```

## 6. セット商品の再帰分解（MVP）
- 方針: 常に抽出器を走らせ、結果が空なら単品扱い。事前の二値判定はしない。
- 再帰の深さ: 1（親アイテムの本文に含まれる関連 item_id を1段だけ展開）
- ヒューリスティクス
  - ファイル名パターン（接頭・中間・接尾）
    - 例: "^Kikyo_", "^Selestia_", "^Kanae_", "_Kikyo", "_Selestia"
  - 本文の明示的列挙
    - "対応アバター: セレスティア、桔梗、かなえ"
    - "for Selestia", "Kikyo用"
  - 商品本文からの関連 item_id 抽出（items/数値）
- アバター辞書（例）
  - Selestia: ["セレスティア","selestia","SELESTIA"]
  - Kikyo: ["桔梗","kikyo","KIKYO","kikyou"]
  - Kanae: ["かなえ","kanae","KANAE","カナエ"]
  - Shinano: ["しなの","shinano","SHINANO"]
  - Manuka: ["マヌカ","manuka","MANUKA"]
  - Moe: ["萌","moe","MOE"]
  - Rurune: ["ルルネ","rurune","RURUNE"]
  - Hakka: ["薄荷","hakka","HAKKA"]
  - Mizuki: ["瑞希","mizuki","MIZUKI"]
- 信頼度と重複排除
  - filename接頭: 0.9、本文明示: 0.95、本文文脈(for/用/対応): 0.8
  - 一定未満（例: 0.75）は破棄
  - avatar_codeで重複統合
- 仮想ID
  - subitem_id = "{item_id}#variant:{avatar_code}:{slug(variant_name)}"
  - slug は ASCII へ簡易変換（または Unicode 許容のどちらかに統一、MVPは ASCII）

### 疑似コード（要点）
```python
def extract_variants_mvp(item_id, visited=set()):
    if item_id in visited:
        return []
    visited.add(item_id)

    page = fetch_with_cache(item_id)
    files = parse_filenames(page)
    text  = extract_text(page)
    links = extract_item_ids(text)

    candidates = []
    candidates += infer_from_filenames(files)       # 高優先
    candidates += infer_from_text(text)             # 明示/文脈
    # 深さ1: 子は解析するが、その先へは潜らない
    for child_id in links:
        child_page = fetch_with_cache(child_id)
        candidates += infer_from_text(extract_text(child_page))

    variants = normalize_and_dedupe(candidates, min_confidence=0.75)
    return variants
```

### item_idに基づく追加データ取得
- item_id だけで /ja/items/{id} を取得し、約1req/sec＋再試行（指数バックオフ）で安定収集。  
- 抽出は JSON-LD 優先→OG/meta→DOM の順で name/shop/creator/image/price/description を取得し、本文から related_ids（items/数値）も抽出（files は任意）。  
- 対応アバターはファイル名・本文・辞書で推定、セット品は avatar 別に Variant 生成（subitem_id 規約、MVP は深さ1）。  
- キャッシュは item_id キーで保存（成功はTTL/手動更新、失敗は24h 再試行抑制）、price 不明時は wish_price でメトリクス補助。  
- 404/429 等の例外処理を実施し、avatar アイテムには自明な targets を付与、メトリクスは有料と無料（free count）を分離可視化。


## 7. メタ取得とキャッシュ
- スクレイピング先: 公開の商品ページ（item_name, shop_name, creator_id, image_url, current_price, canonical_url）
- レート制御: 約1req/sec
- キャッシュ: 単層YAML（booth_item_cache.yml）。取得失敗はエラースタブを保存し再試行頻度を抑制。
- 価格: 取得不可は null。UIでは「—」表示。本文に「無料」等があれば 0 を許容。

## 8. 正規化とシノニム
- アバター名は辞書で正規化し、code（例: "Selestia"）へ統一
- type を唯一の種別フィールドとして使用（category などの別名は使わない）
- 重複排除: 同一 item_id の多重入力、同一ファイルの重複列挙を統合

## 9. 集計（MVP）
- items: type別件数、shop別件数
- variants: avatar別件数、variant_name別件数（上位N）
- Avatar×Costume 組合せ
  - count, total_price, avg_price, median_price
  - 価格は current_price を優先、無ければ wish_price（任意入力）で補完

## 10. ダッシュボード（静的SPA）
- 検索: クライアント側の簡易検索（部分一致/前方一致）。将来はFuse.jsへ拡張。
- フィルタ: type、avatars（複数選択）、shops、価格帯、更新日、タグ
- 一覧: サムネイル、商品名、ショップ、タイプ、対象アバター、現在価格、ファイル、リンク
- 詳細: 画像、説明要約、対象アバター、関連リンク
- セット展開: 親行から variants を展開表示（折りたたみ切替）

## 11. 性能・運用・エラー
- 性能: 数百〜数千件で1秒以内の検索/フィルタを目標（クライアント仮想リスト検討）
- 取得失敗: キャッシュにエラースタブ（timestamp, error）を保存して継続
- ログ: 取得失敗・タイムアウト・レート超過を簡易記録（テキスト/JSON）
- セキュリティ: 認証情報は扱わず公開データのみ

## 12. テスト（MVP）
- ユニット
  - URL→item_id 抽出
  - ファイル名/本文からのアバター推定（日本語・英語混在）
  - 再帰分解（深さ1）、循環検知
- 結合
  - 入力→正規化→メタ取得→セット分解→catalog.yml/metrics.yml→index.html
  - 手動YAMLの上書き（存在時は手動定義を優先）
- 受け入れ基準
  - 指定入力から catalog.yml/metrics.yml が生成される
  - セット内訳が variants として展開され、対象アバターでフィルタ可能
  - Avatar×Costume 組合せランキングが表示される
  - 一覧検索/フィルタ/並び替えが1秒以内で反応

## 13. マイルストーン（MVP→M2）
- M1（MVP）
  - 正規化ETL（単品アイテム）
  - メタ取得＋YAMLキャッシュ（単層）
  - ダッシュボード（一覧・検索・フィルタ）
- M2
  - セット再帰分解（深さ1）実装
  - variants 展開UI
