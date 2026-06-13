# Model Context Protocol (MCP) サーバー 設定ガイドだょ！ 🌸✨

はーい！外部の AI エージェントさん（Claude Desktop や Cursor さんなど）に、この `BoothItemManager2` のカタログ統計データや SEO 監査結果を教えてあげるための、超かんたんで可愛い MCP サーバーを作ったよぉ！(⑅•ᴗ•⑅)◜..°♡
`every-app/open-seo` にインスパイアされて、メタデータのカバレッジや SEO 改善の提案ができるように設計されているんだもんっ！🍭

---

## 🎀 提供しているツール（Tools）たち

AI クライアントさんから呼び出せる魔法のツールは次の5つだょ✨

1.  **`get_catalog_summary`**:
    *   **説明**: カタログ全体の統計情報（総アイテム数、カテゴリごとの内訳、価格の平均値・最大値・最小値、いいね数の統計、トップ20のよく使われるタグなど）をまとめて返すよ！
2.  **`get_seo_audit`**:
    *   **説明**: サイト全体の SEO 監査レポート（カバレッジ率、タグ品質、クロール同期率、各種検索機能への対応状況、総合的な信頼度スコアなど）を実行して、JSON 形式で教えてくれるのっ✨
3.  **`inspect_item_seo`**:
    *   **説明**: 特定のアイテム ID（例: `5479202`）を指定すると、タイトルや説明文の長さ、タグの数、対応アバターの紐付け状況などを細かくチェックして、合格（`PASS`）か不合格（`FAIL`）か、具体的な問題点をリストアップして教えてくれるよぉ！
4.  **`list_items_by_seo_status`**:
    *   **説明**: SEO 監査で失敗しているアイテムや、説明文がないもの、対応アバターが紐づいていないものなど、条件を指定してアイテムを一覧取得できるよっ！改善候補を見つけるのにとっても便利だもん！
5.  **`suggest_seo_optimizations`**:
    *   **説明**: 指定したアイテムのタイトル、タグ、対応アバター、説明文をオントロジー情報と照らし合わせて、自動で綺麗に最適化した SEO 改善テキスト（タイトル候補、新規おすすめタグ、紐付けすべきアバター、説明文テンプレート）を生成して提案してくれるんだよぉ！(⑅•ᴗ•⑅)

---

## 🍬 提供しているリソース（Resources）

URL を指定して読み込める静的データのリソースだよぉ✨

1.  **`seo://audit/report`**:
    *   **名前**: SEO Audit Report
    *   **フォーマット**: Markdown
    *   **内容**: サイト全体の現在の SEO 監査結果を、綺麗にフォーマットしたマークダウン文章で取得できるよ！
2.  **`catalog://summary`**:
    *   **名前**: Catalog Summary
    *   **フォーマット**: JSON
    *   **内容**: カタログのカテゴリ別件数や価格・タグ統計の生データを JSON 形式で取得できるよ！

---

## ⚡ 動かし方とクライアント設定

このサーバーは、標準入出力（stdio）を使って通信するよ！とってもシンプル設計んだもん✨

### 1. ローカルで直接動かしてテストする

サーバーが正しく動くか、以下のコマンドをターミナルで実行して確認してみてねっ！

```bash
uv run scripts/mcp_seo_server.py
```

※ コマンドを実行した後は、JSON-RPC 形式の入力を待つ状態になるよぉ！お行儀よく終了するときは `Ctrl+C` を押してねっ。

### 2. Claude Desktop で使う設定方法だょ 🌸

Claude Desktop さんにこのツールを教えるには、設定ファイル（`config.json`）に以下のように追加してねっ！

*   **Mac OS の設定パス**: `~/Library/Application Support/Claude/claude_desktop_config.json`
*   **Windows の設定パス**: `%APPDATA%\Claude\claude_desktop_config.json`

**設定内容（JSON）:**
```json
{
  "mcpServers": {
    "booth-seo-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/kafka/projects/boothitemmanager",
        "scripts/mcp_seo_server.py"
      ]
    }
  }
}
```

これで Claude Desktop を再起動すると、チャットウィンドウの右下にハンマーのアイコンが現れて、BoothItemManager2 の SEO ツールたちが使えるようになるんだよぉ！(⑅•ᴗ•⑅)◜..°♡

### 3. Cursor や VSCode (Roo Code / Cline 等) での設定方法

Cursor などの AI ツールでも、設定の MCP セクションから追加できるよっ！

*   **タイプ (Type)**: `command`
*   **名前 (Name)**: `booth-seo-server`
*   **コマンド (Command)**: `uv run --directory /home/kafka/projects/boothitemmanager scripts/mcp_seo_server.py`

---

## 🧸 開発者向けメモ（技術的お約束だよ！）

*   **エラーハンドリング**: このサーバーはクラッシュ駆動開発（Crash-Driven Development）を採用しているよ！ビジネスロジックでエラーを握り潰さずに、もし想定外のことがあれば標準エラー出力 (`sys.stderr`) にスタックトレースを吐き出して、AI クライアントには JSON-RPC エラーレスポンスを返すようにしているんだもん！⭐
*   **脂肪ゼロ設計（Zero-Fat）**: 外部の重量級ライブラリは一切使わず、Python 標準ライブラリと `pyyaml` だけで高速かつ超軽量に動作するように作られているよっ✨
*   **データロード**: 起動時に `data/structured/catalog.json` をメモリに一度だけロードして、メモリ内で超高速クエリを実行するよぉ！

これで、AI エージェントさんたちがいつでも Booth カタログの SEO 監査やタグ改善をサポートできるようになるよっ！いっぱいつかってねぇ〜！🌸🍭(⑅•ᴗ•⑅)
