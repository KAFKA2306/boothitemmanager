# 🌸 BoothItemManager2 パイプライン詳細手順書だょ！🌸

このドキュメントは、データ収集から検索インデックス構築までの各フェーズの詳細な動作と、実行手順についてまとめたものだょぉ🧸✨

---

## 🐾 1. Crawler Agent 起動 (Crawler Agent Launch)

BOOTHのアイテム情報を自動収集する巡回エージェントを起動するフェーズだょ✨

- **実行コマンド**:
  ```sh
  uv run python3 run_boothitemmanager2.py
  ```
- **仕組み**:
  `src/boothitemmanager2/agents/crawler.py` が動作し、対象のBooth IDリスト（`input/discovered_ids.txt`等）をもとに、並行してページのリクエストを送信してHTMLを取得するの(⑅•ᴗ•⑅)◜..°♡

---

## 🐾 2. Raw データ蓄積 (Raw Data Accumulation)

クローラーが持ってきた情報を安全に保存し、系譜（Provenance）を保証するフェーズだょ🍭

- **格納先**:
  - `input/raw/{item_id}.html` (生の商品ページ)
  - `data/raw/index.ndjson` (バルク用生データインデックス)
- **ルール**:
  保存されたHTMLファイルはSHA-256ハッシュで検証可能になっていて、不正な改ざんを防ぐゼロトラスト設計になっているんだもん✨

---

## 🐾 3. Normalizer 実行 (Normalizer Execution)

生HTMLから不要なボイラープレートや個人情報（PII）を取り除き、タグ情報を抽出・正規化するフェーズだょ🎨

- **核となるモジュール**:
  - `src/boothitemmanager2/agents/normalizer.py`
- **特徴**:
  オントロジー（`ontology/tags.yaml`, `ontology/styles.yaml`）に登録された数千のエイリアスと自動マッチングを行い、服のタイプ、色、対応アバターなどを高い精度で割り振るよぉ！近傍30文字の否定検出（「非対応」等）も含んでいるの🧸

---

## 🐾 4. DB 構築 (DB Construction)

正規化されたアセットデータを構造化JSONデータベースファイルとして出力するフェーズだょ🐾

- **核となるモジュール**:
  - `src/boothitemmanager2/agents/db_builder.py`
- **格納先**:
  - `data/structured/catalog.json`
- **仕組み**:
  高速なフィルタリングや集計処理ができるように、正規化済みのデータを綺麗な配列データ形式に整形して書き出すの✨

---

## 🐾 5. Graph Builder

アセット同士の関連性やタグのつながりを可視化する network を組み立てるフェーズだょ🍭

- **核となるモジュール**:
  - `src/boothitemmanager2/agents/tag_graph_builder.py`
- **出力先**:
  - `api/tag_graph.json`
- **仕組み**:
  アイテム同士の共起（同時に付与されているタグ等）を計算し、ジャカード係数を用いた関連度スコアを計算して、エッジとノードの関係を構築するよぉ！(๑•̀ㅂ•́)و✧

---

## 🐾 6. Search Index 構築 (Search Index Construction)

フロントエンドダッシュボードがサーバーレスで超高速に動作するための静的JSONインデックスを生成するフェーズだょ✨

- **核となるモジュール**:
  - `src/boothitemmanager2/agents/search_builder.py`
  - `src/boothitemmanager2/agents/api_generator.py`
- **出力先**:
  - `api/search_index.json`
  - `api/catalog_summary_part1.json`
- **仕組み**:
  すべてのアイテム情報をスキーマ検証（`ontology/schema.json`）に通したあと、ブラウザ側で検索・フィルタリングしやすい構造に最適化して書き出すの(⑅•ᴗ•⑅)◜..°♡

---

## 🌸 各パイプライン工程の具体的監査基準 (Audit Criteria) 🌸

JSONファイルの中身を人間が1つずつ見なくても、以下の自動監査スクリプトを実行することで、パイプライン全体が正常に動作したかを一発で判定できるよぉ！🐾✨

### 🐾 監査実行コマンド
```sh
uv run python3 scripts/audit_pipeline.py
```

### 🐾 各工程の合否判定ルール
1. **Step 1: Crawler Agent 起動**
   - **基準**: `input/discovered_ids.txt` が存在し、巡回ターゲットとなるBooth商品IDが1つ以上登録されていること。
2. **Step 2: Rawデータ蓄積**
   - **基準**: クローリングされた生データ NDJSON (`data/raw/index.ndjson`) が存在し、ファイルサイズが0より大きいこと。
3. **Step 3: Normalizer 実行**
   - **基準**: 構造化カタログ内の全アイテムに対してカテゴリ判定が行われており、未分類（`ASSET`）以外の明確に分類されたアイテムの比率（分類精度率）が一定水準を超えていること。
4. **Step 4: DB 構築**
   - **基準**: `data/structured/catalog.json` が有効なJSON形式として正しく読み込め、レコード数が入力アイテム数と完全に一致していること。
5. **Step 5: Graph Builder**
   - **基準**: `api/tag_graph.json` が生成され、共起強度が計算されたノード（nodes）とエッジ（edges）が構築されていること。
6. **Step 6: Search Index 構築**
   - **基準**: `api/search_index.json` が生成され、スキーマに完全適合した検索可能な商品データの総数が正しく書き出されていること。
