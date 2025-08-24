## 入力（input）

### 1) 読み込み元とファイル形式
- 入力ディレクトリ
  - 既定: input ディレクトリ（CLIで --input-dir により変更可）
- サポート形式（拡張子）
  - YAML（.yaml / .yml）
  - Markdown（.md）
  - CSV（.csv）
- 重複排除
  - すべての形式を読み込んだ後、item_id（数値）で重複排除

### 2) item_id の抽出
- テキスト中/URL中からの正規表現抽出を実装
  - 例: “.../items/1234567”, “items/1234567” 等から 1234567 を取得
- 不正な item_id（欠損/非数/0以下）はスキップ

### 3) 形式別の取り込み仕様
- YAML（期待構造）
  - ルートに booth_purchases 配列を想定
  - 各要素の想定フィールド
    - id: number（必須。item_id）
    - name: string（任意）
    - author: string（任意）
    - category: string（任意）
    - variation: string（任意）
    - files: string[]（任意。ダウンロードファイル名等）
    - notes: string（任意）
    - wish_price: number（任意）
- Markdown
  - 行単位でURL（または [タイトル](URL)）を走査
  - URLから item_id を抽出
  - タイトルがあれば name に反映
- CSV
  - item_id 抽出は id / item_id / url / link のいずれかの列から
  - 受け取り可能な列の例（任意）：name/title, author/creator/shop, category/type, variation/variant, notes/memo, price/wish_price

### 4) 正規化前の中間モデル（RawItem）
- フィールド
  - item_id: int（必須）
  - name, author, category, variation, notes: string|null
  - files: string[]（省略時は空配列）
  - wish_price: int|null
  - url: string（item_id から組み立て。正規化時のフォールバックに使用）

## 変換・取得（scrape → normalize）

### 1) スクレイピング（BoothScraper）
- 入力: item_id
- レート制御
  - 最低1秒間隔での実行
  - タイムアウト/HTTPエラー時はエラースタブをキャッシュ（再試行を抑制）
- キャッシュ
  - 既定ファイル名: booth_item_cache.json（CLIで --cache-file 指定可）
  - 成功・失敗ともに scraped_at を付与して保存
- 取得メタ（ItemMetadata）
  - item_id: int
  - name: string|null
  - shop_name: string|null
  - creator_id: string|null（ショップリンクやURL末尾から推定）
  - image_url: string|null（絶対URLに解決）
  - current_price: int|null（数値抽出。無料判定は0）
  - description_excerpt: string|null（本文から先頭約200字）
  - canonical_url: string|null（アイテムの正規URL相当）
  - files: string[]（非ログイン環境では取得不可の場合あり）
  - updated_at: string|null（ページの更新日時等が読めた場合）
  - scraped_at: string（ISO8601）
  - error: string|null（HTTP 404など）
- 備考
  - DOMの複数セレクタでフォールバック抽出
  - “無料 / free / ¥0” を検出した場合は current_price=0
  - ファイル名一覧は表示されないことが多いため、取得できないケースを許容

### 2) 正規化（DataNormalizer）
- 型（type）正規化
  - 入力 category を定義マップで正規化
  - 不明時は 'other'
  - 一部の実装では名称/本文からのキーワード判定による補完あり
- ファイル正規化（FileAsset）
  - 入力 files の各要素から {filename, version, size, hash} を生成
  - version はファイル名の “v1.2 / Ver1.2 / _1.2_” 等から抽出
- 対象アバター（targets: AvatarRef[]）
  - 抽出元
    - ファイル名の接頭/接尾（例: Kikyo_*, *_Kikyo）
    - 名称/説明の明示（例: “対応アバター: セレスティア、桔梗、かなえ”）
    - “for Selestia / Kikyo用” の言い回し
  - 対応辞書（主なコード）
    - Selestia, Kikyo, Kanae, Shinano, Manuka, Moe, Rurune, Hakka, Mizuki
  - AvatarRef は {code, name}（name は日本語表記）
- URL・日時
  - url は metadata.canonical_url があればそれを採用、なければ RawItem.url を使用
  - updated_at は metadata.updated_at があれば採用、なければ現在時刻（ISO8601）
- 追加（実装差分あり）
  - 一部コードでは「セット商品」のバリアント（variants）を生成する機能を内包
    - ファイル名のアバター別プレフィクスや本文の列挙から、subitem_id を生成
    - subitem_id 形式: "{parent_item_id}#variant:{avatar_code}:{slug(variant_name)}"