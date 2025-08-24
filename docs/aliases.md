# 提案: aliases.yml（完全版）とタイプ推定ロジック/targets自動付与の改善

以下はそのまま保存して利用できる aliases.yml の完全版（2025-08-24版）。既存9アバターに加え、catalog.yml や入力ファイルで登場した SUN / INABA / 椎名 / 狐雨 / 猫メイド を正規コードとして追加しています。また、タイプ種別の表記ゆれには、報告のあった「gimick（誤字）」「Texture（大文字）」「Goods」などを正規化するエイリアスを収録しました。

重要ポイント
- options: 文字前処理をNFKC＋大小無視で一元化
- avatars: 既存9件＋新規5件（SUN/INABA/Shiina/KitsuneAme/NekoMaid）
- types: 誤字・大小・和英表記に広く対応（gimick, Texture, Goods など）
- “髪型/ヘア/帽子/眼鏡/靴”などは accessory に正規化
- “ModularAvatar/システム/System/ギミック”は gimmick に正規化
- “ボディ/肌/瞳/眉/リップ/ネイル/テクスチャ”は texture に正規化
- “ワールド/背景/ステージ/マップ/シーン/ロケーション/カフェ”は world に正規化
- “フルセット/セット/パック/コレクション”は bundle に正規化
- “グッズ/Goods/物販/アクスタ/ステッカー”は other に正規化

保存用ファイル: aliases.yml

```yaml
version: 1
updated_at: "2025-08-24"

options:
  # 文字正規化の基本方針（実装側で可能なら適用）
  case_insensitive: true           # 大文字小文字を区別しない
  unicode_normalization: "NFKC"    # 全角/半角や互換文字を正規化
  trim_whitespace: true            # 前後の空白を除去
  collapse_inner_spaces: true      # 連続スペース/タブ/全角空白の圧縮
  strip_symbols:
    - "_"
    - "-"
    - "–"
    - "—"
    - "・"
  dedupe_aliases: true             # 重複エイリアスを自動削除

avatars:
  Selestia:
    name_ja: "セレスティア"
    name_en: "Selestia"
    aliases:
      - "セレスティア"
      - "selestia"
      - "SELESTIA"
      - "Celestia"
      - "celestia"
      - "せれすてぃあ"

  Kikyo:
    name_ja: "桔梗"
    name_en: "Kikyo"
    aliases:
      - "桔梗"
      - "kikyo"
      - "KIKYO"
      - "kikyou"
      - "Kikyou"
      - "KIKYOU"
      - "ききょう"
      - "キキョウ"

  Kanae:
    name_ja: "かなえ"
    name_en: "Kanae"
    aliases:
      - "かなえ"
      - "カナエ"
      - "kanae"
      - "KANAE"
      - "카나에"

  Shinano:
    name_ja: "しなの"
    name_en: "Shinano"
    aliases:
      - "しなの"
      - "シナノ"
      - "shinano"
      - "SHINANO"

  Manuka:
    name_ja: "マヌカ"
    name_en: "Manuka"
    aliases:
      - "マヌカ"
      - "manuka"
      - "MANUKA"

  Moe:
    name_ja: "萌"
    name_en: "Moe"
    aliases:
      - "萌"
      - "もえ"
      - "モエ"
      - "moe"
      - "MOE"

  Rurune:
    name_ja: "ルルネ"
    name_en: "Rurune"
    aliases:
      - "ルルネ"
      - "rurune"
      - "RURUNE"

  Hakka:
    name_ja: "薄荷"
    name_en: "Hakka"
    aliases:
      - "薄荷"
      - "はっか"
      - "ハッカ"
      - "hakka"
      - "HAKKA"

  Mizuki:
    name_ja: "瑞希"
    name_en: "Mizuki"
    aliases:
      - "瑞希"
      - "みずき"
      - "ミズキ"
      - "mizuki"
      - "MIZUKI"

  # 追加（カタログに登場するが targets 付与漏れ対策）
  SUN:
    name_ja: "SUN"
    name_en: "SUN"
    aliases:
      - "SUN"
      - "Sun"
      - "サン"

  INABA:
    name_ja: "INABA"
    name_en: "INABA"
    aliases:
      - "INABA"
      - "Inaba"
      - "いなば"
      - "イナバ"

  Shiina:
    name_ja: "椎名"
    name_en: "Shiina"
    aliases:
      - "椎名"
      - "Shiina"
      - "SHIINA"
      - "しいな"
      - "シイナ"

  KitsuneAme:
    name_ja: "狐雨"
    name_en: "KitsuneAme"
    aliases:
      - "狐雨"
      - "kitsuneame"
      - "KITSUNEAME"
      - "キツネアメ"
      - "きつねあめ"
      # 読みが不確実な場合は日本語表記の一致を優先

  NekoMaid:
    name_ja: "猫メイド"
    name_en: "NekoMaid"
    aliases:
      - "猫メイド"
      - "ネコメイド"
      - "nekomaid"
      - "NekoMaid"
      - "neko maid"
      - "ネコ メイド"

types:
  avatar:
    aliases:
      - "アバター"
      - "avatar"
      - "AVATAR"
      - "3D Avatar"
      - "3D avatar"
      - "3Dアバター"
      # 3Dモデルは曖昧性が高いためここでは敢えて含めない（下記ロジックで判定）

  costume:
    aliases:
      - "衣装"
      - "コスチューム"
      - "服"
      - "アウトフィット"
      - "outfit"
      - "costume"
      - "COSTUME"
      - "3D Clothing"
      - "3D clothing"
      - "フルセット"
      - "Full set"
      - "ドレス"
      - "スカート"
      - "水着"
      - "浴衣"
      - "セーラー"
      - "メイド服"
      - "トップス"
      - "ボトムス"
      - "アウター"

  accessory:
    aliases:
      - "アクセサリ"
      - "アクセサリー"
      - "accessory"
      - "ACCESSORY"
      - "3D Accessory"
      - "髪型"
      - "ヘア"
      - "ヘアスタイル"
      - "Hair"
      - "帽子"
      - "Hat"
      - "眼鏡"
      - "メガネ"
      - "Glasses"
      - "ピアス"
      - "イヤリング"
      - "靴"
      - "シューズ"
      - "靴下"
      - "アクセ"

  tool:
    aliases:
      - "ツール"
      - "tool"
      - "TOOL"
      - "Unity"
      - "Editor"
      - "エディタ"
      - "インストーラ"
      - "Installer"
      - "Script"
      - "スクリプト"
      - "unitypackage"
      - "ユニティ"

  gimmick:
    aliases:
      - "ギミック"
      - "gimmick"
      - "GIMMICK"
      - "gimick"     # 誤字対策
      - "ModularAvatar"
      - "モジュラーアバター"
      - "System"
      - "システム"
      - "仕組み"
      - "機能"
      - "寝返り"
      - "OVR"
      - "アニメーション制御"

  world:
    aliases:
      - "ワールド"
      - "world"
      - "WORLD"
      - "シーン"
      - "ステージ"
      - "背景"
      - "マップ"
      - "ロケーション"
      - "空間"
      - "ステージセット"
      - "カフェ"
      - "Cafe"
      - "会場"
      - "会場セット"

  texture:
    aliases:
      - "テクスチャ"
      - "Texture"
      - "TEXTURE"
      - "素材"
      - "material"
      - "MAT"
      - "スキン"
      - "skin"
      - "肌"
      - "ボディ"
      - "ボディテクスチャ"
      - "顔"
      - "フェイス"
      - "リップ"
      - "唇"
      - "眉"
      - "まゆ"
      - "まつげ"
      - "瞳"
      - "目"
      - "虹彩"
      - "nail"
      - "ネイル"

  scenario:
    aliases:
      - "シナリオ"
      - "scenario"
      - "SCENARIO"
      - "台本"
      - "ストーリー"
      - "物語"
      - "セリフ"

  bundle:
    aliases:
      - "セット"
      - "セット商品"
      - "bundle"
      - "BUNDLE"
      - "フルセット"
      - "Full set"
      - "パック"
      - "Pack"
      - "コレクション"
      - "Collection"

  other:
    aliases:
      - "グッズ"
      - "Goods"
      - "物販"
      - "アクスタ"
      - "ステッカー"
      - "GOODS"
      - "小物（分類不明）"
```

***

## あるべき type 推定ロジック（誤分類の再発防止）

報告の誤分類と対策
- RBS SuiminSystem 2 → 正しくは gimmick（または tool）
  - ヒント語: 「ModularAvatar対応」「システム」「メニュー操作なし」「OVR」「高さ調整」→ gimmick を優先
- 「ぬるてか水滴ボディテクスチャ」 → 正しくは texture
  - ヒント語: 「ボディ」「テクスチャ」「スキン」→ texture を優先（大小無視）
- 「【3Dモデル】のらなべやカフェセット」 → world あるいは other
  - ヒント語: 「カフェ/背景/ステージ/シーン/ワールド」→ world を優先
  - ワールド系キーワード不在かつ “グッズ/小物（分類不明）”なら other

推奨アルゴリズム（優先度式・スコアリング）
1) 事前正規化
   - NFKC＋大小無視＋記号除去（options 準拠）
2) 強キーワード即時決定（高優先度）
   - gimmick: ModularAvatar/モジュラーアバター/システム/System/ギミック/OVR
   - texture: テクスチャ/スキン/肌/ボディ/瞳/眉/リップ/ネイル
   - world: ワールド/背景/ステージ/シーン/マップ/空間/カフェ
   - tool: Unity/Editor/エディタ/インストーラ/スクリプト
   - accessory: 髪型/ヘア/帽子/眼鏡/靴/ピアス/イヤリング
   - costume: 衣装/服/ドレス/スカート/水着/浴衣/セーラー/メイド服
3) 複合語の打ち消しルール（例）
   - “3Dモデル”単体では決めない（avatar/prop/world いずれもあり得る）
   - “フルセット/セット/パック/コレクション”は bundle に加点（単独決定はしない）
4) 複数カテゴリヒット時の優先順位
   - gimmick > tool > world > texture > accessory > costume > scenario > bundle > other
   - ただし、bundle は「構成」概念なので、他カテゴリ（例: costume）と同時ヒット時は「中身優先」か「bundle」とするか運用で統一
5) ファイル名の補助
   - “*_Material*/*_PSD*/*_Texture*”→ texture 加点
   - “Kikyo_* / Selestia_*” → costume 加点
   - “*_v*.unitypackage / unitypackage.zip” → tool 加点
6) 最後の手段
   - types エイリアス辞書の一致結果を採用
   - それでも未決なら other

実装ヒント（normalize._infer_type_from_text 改良の骨子）
- 既存の type_keywords を「優先度付き dict（上記順）」に再構成し、命中スコア方式に変更
- “3Dモデル”は avatar に含めない（曖昧性を避ける）
- “bundle”は補助フラグ扱い（variants 生成の判断に寄与）

***

## type: avatar の targets 自動付与の漏れ対策

症状
- SUN, INABA, 椎名, 狐雨, 猫メイドのアバターが avatar と認識されても targets が空

対策（3点）
1) アバター辞書の拡充
   - 本回答の aliases.yml に5件を追加済み
2) 自動付与ロジックの強化（_auto_assign_avatar_targets）
   - 対象文字列: item.name + description_excerpt + 全ファイル名
   - パターン:
     - 日本語括弧名: 「SUN」「椎名」
     - ローマ字/英字: SUN / INABA / Shiina
     - 固有ファイル名: SUN_v*, 01_INABA_*, 01Shiina_*, 狐雨ver*, 猫メイド*
   - ヒット時に辞書の AvatarRef を1件追加（重複排除）
3) avatar タイプの強制ターゲット付与
   - item.type == 'avatar' かつ targets が空なら、上記パターンで最初にマッチしたアバターを必ず付与
   - それでも見つからない場合は、名称から最長一致/辞書走査で候補抽出（1件に限定）

ユニットテスト案
- "「SUN －サン－」ver1.1.3" → targets=[{code:SUN, name:SUN}]
- "01_INABA_ver4.0.1.zip" を files に含む avatar → targets=[INABA]
- "狐雨ver.2.0.0.zip" または 名称に「狐雨」 → targets=[KitsuneAme]
- “猫メイド”含有 → targets=[NekoMaid]
- 既存9アバターの英日混在（Kanae/KIKYO/セレスティア/薄荷 等）も同時確認

***

## 運用メモ（反映の仕方）

- aliases.yml はリポジトリ直下（または config/）に配置し、ロード時に options に従って文字正規化を適用。
- DataNormalizer に aliases.yml を読ませ、AvatarDictionary/Type 正規化を動的に構築。
- type 推定は:
  1) 入力 category の正規化(types) → 2) 強キーワード即決 → 3) スコア集計 → 4) ファイル名補助 → 5) 最終フォールバック（other）
- variants 生成では、bundle/複数アバター/複数プレフィクスの兆候があれば展開。
- 既存データに対し、ETLを再実行するだけで:
  - RBS SuiminSystem 2 は gimmick（or tool）に
  - 「ぬるてか水滴ボディテクスチャ」は texture に
  - 「【3Dモデル】のらなべやカフェセット」は world（該当語が無ければ other）に
  - SUN/INABA/椎名/狐雨/猫メイドの avatar タイプには targets が自動付与

上記で、報告いただいた3つの課題（gimick/Texture/Goods の正規化、type 推定の精度改善、avatar の targets 付与漏れ）を同時に解消できます。
