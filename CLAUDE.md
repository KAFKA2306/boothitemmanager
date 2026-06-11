# 🌸 CLAUDE.md だよぉ！🌸

## 🎀 プロジェクト概要 (Project)
**BoothList**: BOOTHのアセットダッシュボードを生成するシステムだよ(⑅•ᴗ•⑅)◜..°♡

## 🏗️ アーキテクチャ (Architecture)
- **ETLパイプライン**: Input ➡️ Scrape ➡️ Normalize ➡️ Export
- **技術スタック**: Python, PyYAML, BeautifulSoup4, HTML/JS だもん！🍭

## 🛠️ 開発コマンド (Development)
- **一括実行 (Bulk)**: `.venv/bin/python run_bulk_pipeline.py`
- **個別実行 (Selective)**: `.venv/bin/python run_boothitemmanager2.py`
- **ビルド**: `task build` (一括パイプラインを実行するよぉ！)
- **ローカル起動**: `task serve` (http://localhost:8080 で `dist/` をサーブするの✨)
- **設定ファイル**: [config.yaml](file:///home/kafka/projects/boothitemmanager/config.yaml)
- **出力先**: `dist/` および `api/`
- **ID抽出スクリプト**: `.venv/bin/python -m boothlist.extract_ids`
  - 標準入力からテキストを読み込んでBooth IDを抽出し、`input/YYYYMMDD.txt` に保存するよぉ！

## 📄 主要ファイル (Key Files)
- [run_bulk_pipeline.py](file:///home/kafka/projects/boothitemmanager/run_bulk_pipeline.py): 一括データ処理のメインエントリーだもん！
- [run_boothitemmanager2.py](file:///home/kafka/projects/boothitemmanager/run_boothitemmanager2.py): 個別クロールのオーケストレーターだよ。
- [api_generator.py](file:///home/kafka/projects/boothitemmanager/src/boothitemmanager2/agents/api_generator.py): 静的JSON APIの生成エージェントだよぉ🍭
- [index.html](file:///home/kafka/projects/boothitemmanager/index.html): フロントエンドダッシュボード（`api/` のデータを使用するよ！）