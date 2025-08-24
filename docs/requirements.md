# requirements.md — BOOTH資産ダッシュボード再構築要件

## 1. 背景とゴール
- BOOTHで購入済みのアバター/衣装/アクセサリ/ツール類を、検索・分析・可視化できる「利活用しやすい」ダッシュボードをゼロから再設計する。
- 既存のスクリプト構成や実装は参考に留め、データモデル/抽出ロジック/UIを含めて破壊的に再構築する。
- 特に衣装フルセット等の「セット商品」を“再帰的に分解”し、可能な限り下位要素のID・対応アバター・バリアントを識別して紐付ける。

## 2. スコープ
- 対象データ: BOOTHの購入済み商品（アバター、衣装、アクセサリ、ギミック/ツール、ワールド、テクスチャ/素材、シナリオ素材等）
- 対象機能: データ収集（yml/Google Sheets/手動YAML）、メタ取得（スクレイピング+キャッシュ）、セット再帰分解、正規化、分析（組合せ）、ダッシュボード表示、エクスポート/公開
- 非対象（初期リリース）: ログインが必要なAPI連携、購入価格の正確な自動復元（初期は「現在価格」または手入力の希望価格を使用）

## 3. 用語定義
- アイテム（Item）: BOOTH上の1商品（一意の数値item_id）
- セット商品: 1アイテムに複数アバター向けファイル/バリアントを内包する商品
- サブアイテム（Variant/Subitem）: セット商品内のアバター別・バリアント別の下位要素（仮想IDで表現）
- 対象アバター: その衣装/素材等の対応モデル（例: セレスティア、桔梗、かなえ）

## 4. 主要ユースケース
- 所持品の高速検索とフィルタ（タイプ、対象アバター、ショップ、価格帯、タグ）
- アバター別に「適用可能な衣装/アクセサリ」を一覧化
- 衣装フルセットの中身を再帰展開し、対象アバターごとに把握
- ダウンロードファイルのバージョン・差分把握、最新版の検出
- 静的サイトとしてエクスポートし、GitHub Pages等で閲覧

## 5. 機能要件

### 5.1 データ入力
- 入力ソース
  - boothの購入履歴一覧をコピペしたもの: .input/*
    - 正規化し、booth.ymlとしてデータシートを成形する必要がある

### 5.2 メタ情報取得
- アイテムページから以下を取得（HTMLスクレイピング）
  - item_name, shop_name, creator_id（サブドメイン等から推定）, image_url, current_price, canonical_url
- キャッシュ
  - yml（booth_item_cache.yml）に永続化

### 5.3 セット商品の再帰分解（重要）
- 目的: セット商品を対象アバター/バリアント単位に分割し、検索・集計・互換性表示を可能にする
- 手段
  - ページ本文・添付リンク・ダウンロードファイル名からのヒューリスティック抽出
  - 既知アバター辞書（Kanae, Kikyo, Selestia, Shinano, Manuka, Moe, Rurune, Hakka 等）のパターン照合
  - 商品説明内の他アイテムURL（items/数値）を抽出して関連/下位として候補化
  - ダウンロードファイル名の規則（例: Kikyo_*, Selestia_*）で対象アバターを推定
- 再帰
  - 抽出した関連アイテムが更にセットの場合、最大深さ2で再帰分解（循環検出・Visited集合で防止）
- 仮想IDの付与
  - subitem_id = "{parent_item_id}#variant:{avatar_code}:{variant_name}" のような一意キー
  - subitemは親アイテムに紐づくが、独立にフィルタ/集計可能
  - セット商品の循環先で実際にboothでのidがある場合も多いので、これを調査する必要がある。

### 5.4 データ正規化
- 正規化スキーマに変換（Item/Variant/Avatar/Shop/Files/Tags/Purchase）
- シノニム正規化（例: “桔梗”と“Kikyo”を同一Avatarに統合）
- 型/単位の統一（価格は整数JPY、日付はISO8601、言語はja優先）
- 重複排除（同一item_idの多重入力、同一ファイルの多重列挙）

### 5.5 ダッシュボード（静的/クライアントサイド）
- グローバル検索（商品名/ショップ/対象アバター/タグ/ID）
- フィルタ
  - タイプ（アバター/衣装/アクセ/ツール/ギミック/ワールド/テクスチャ/シナリオ）
  - 対象アバター（複数選択）
  - 価格帯、ショップ、購入/更新日、タグ
- 一覧テーブル
  - サムネイル、商品名、ショップ、タイプ、対象アバター、現在価格、購入メモ（任意）、ダウンロードファイル一覧、リンク
  - 仮想サブアイテムを行として表示切替（親まとめ/展開）
- 詳細パネル
  - 商品画像、説明要約、対象アバター、関連（親/子/同シリーズ）、外部リンク
- 分析
  - アバター別対応衣装一覧
  - トレンド（期間別件数/支出; 価格は「希望価格」入力または現在価格で代替）
  - 互換性マトリクス（アバター行 × 衣装列の保有/未保有/互換推定）
- 使い勝手
  - 保存フィルタ/並び順、ymlエクスポート、キーボード操作
  - パフォーマンス（数百〜数千件を快適に操作）

### 5.6 エクスポート/公開
- ビルド成果物
  - catalog.yml（正規化カタログ）
  - metrics.yml（集計/ランキング）
  - index.html + assets（静的SPA）
- 公開
  - GitHub Pages等に置くだけで動作
  - GitHub Actionsで定期更新（任意）

### 5.7 将来拡張（任意）
- 簡易編集UI（タグ付け、手動内訳定義）

## 6. 非機能要件
- 信頼性: 取得失敗時もキャッシュで継続
- 拡張性: 取得器（Fetcher）/抽出器（Extractor）/正規化器をプラガブルに
- セキュリティ: 認証情報を保持しない（公開データのみ）、CORS不要な構成

## 7. データモデル（yml想定）

- Item
  - item_id: number
  - type: enum["avatar","costume","accessory","tool","gimmick","world","texture","scenario","bundle","other"]
  - name, shop_name, creator_id, image_url, url
  - current_price: number|null
  - description_excerpt: string|null
  - files: FileAsset[]
  - targets: AvatarRef[] 例: [{code:"Selestia", name:"セレスティア"}]
  - tags: string[]
  - updated_at: datetime
- Variant（Subitem）
  - subitem_id: string（親ID#variant:...）
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
  - version: string|null（ファイル名/文言から推定）
  - size: number|null
  - hash: string|null（任意）
- PurchaseRecord（任意）
  - timestamp: datetime
  - avatar_item_id: number|null
  - costume_item_id: number|null
  - wish_price: number|null
- LinkRef
  - item_id: number
  - relation: enum["related","child","parent","series"]

## 8. 処理フローとロジック

1) 取り込み
- yml/Sheetsを読み込み、URLからitem_id抽出（items/(\d+)）
- 欠損/重複チェック、標準化

2) メタ取得
- item_idごとにページ取得→必要メタ抽出→キャッシュ保存
- 失敗はエラーとして記録しフォールバック

3) セット抽出（1段目）
- 本文/リンク/ファイル名から対象アバター/関連item_id/バリアント候補を抽出
- 既知アバター辞書・正規表現でマッピング

4) 再帰分解（2段目まで）
- 関連item_idがセット性を持つ場合、同様に抽出
- 循環防止（visited set）、深さ制限（max_depth=2）

5) 手動YAMLマージ
- 手動定義のサブアイテム/対象アバターがあれば上書き
- 競合は手動優先

6) 正規化
- Item/Variant/Avatar/Filesへ分割、エイリアス統合
- 仮想サブアイテムに固有キー付与

7) 集計
- アバター別衣装可視、Avatar×Costume組合せ（件数・合計・平均・中央値）
- タイプ別/ショップ別/期間別集計

8) 出力
- catalog.yml、metrics.yml、index.html

## 9. セット再帰ロジック詳細（擬似コード）

```
def extract_variants(item_id, depth=0, visited=set()):
  if depth > MAX_DEPTH or item_id in visited:
      return []
  visited.add(item_id)

  page = fetch_page(item_id)        # キャッシュ利用
  files = parse_files(page)         # 添付ファイル一覧
  text  = parse_text(page)          # 商品名/説明/見出し
  links = parse_item_links(page)    # items/\d+ のURL→子候補IDs

  # 1) ファイル名から対象アバター/バリアント推定
  candidates = infer_from_filenames(files)   # 例: "Kikyo_*" → avatar="Kikyo"
  # 2) テキストから対象アバター/バリアント推定
  candidates += infer_from_text(text)
  # 3) 既知アイテムリンクの展開（再帰）
  for child_id in links:
      candidates += extract_variants(child_id, depth+1, visited)

  # 4) 正規化（アバター辞書へマッピング、重複排除）
  variants = normalize_and_dedupe(candidates)

  # 5) 仮想ID付与
  for v in variants:
      v.subitem_id = f"{item_id}#variant:{v.avatar_code}:{slug(v.variant_name)}"

  return variants
```

- ヒューリスティック例
  - ファイル名が “Kikyo_”, “Selestia_”, “Kanae_” で始まる
  - “for セレスティア / For Selestia” 等の文言を含む
  - “対応アバター: …” の列挙
- 除外
  - 汎用素材/単一ZIPしかない場合はサブアイテム化しない
  - 広告的な外部リンク、重複リンクは無視

## 10. UI要件（画面/コンポーネント）

- 画面
  - ダッシュボード（集計カード、最近更新、ランキング）
  - アイテム一覧（表、詳細パネル）
  - アバター別ビュー（対象アバター→対応衣装/アクセ）
  - 互換マトリクス（アバター×衣装）
  - セット展開ビュー（親子ツリー）
  - 設定（データ更新、キャッシュ、テーマ）
- コンポーネント
  - 検索バー（インクリメンタル/Fuse.js等）
  - フィルタピルズ（タグ/タイプ/アバター）
  - テーブル（仮想化/列表示切替/固定ヘッダ）
  - 詳細ドロワー（画像/説明/リンク/ファイル）
  - 展開/折りたたみ（セット→サブアイテム）

## 11. 運用要件
- 更新
  - ローカル実行（Python ETL）→ yml/html出力
  - GitHub Actionsでスケジュール更新（例: 毎週）
- ログ/監視
  - 取得失敗/タイムアウト/レート超過を記録
  - 差分ログ（前回と今回のメタ差）

## 12. テスト/受け入れ基準
- ユニット
  - URL→item_id抽出の網羅テスト
  - ファイル名/本文から対象アバター推定のテスト
  - 再帰分解の深さ/循環検知テスト
- 結合
  - yml→正規化yml→ダッシュボード表示までの一連
  - 手動YAML上書きの優先動作
- 受け入れ基準（抜粋）
  - 指定yml/Sheetsからcatalog.yml/metrics.ymlが生成される
  - セット商品の内訳がサブアイテムとして展開され、対象アバターでフィルタ可能
  - Avatar×Costume組合せランキングが表示される
  - 一覧検索/フィルタ/並び替えが1秒以内で反応

## 13. マイルストーン（提案）
- M1: データモデル/ETL最小実装（単品アイテム）→ 一覧/検索
- M2: セット再帰分解（深さ1）→ アバター別ビュー
- M3: 再帰深さ2/手動YAML上書き → 互換マトリクス
- M4: 公開パイプライン（GitHub Pages）/キャッシュ運用