# 開発時に最初に読む内容

このファイルだけで作業を開始できるようにする。大きな生成データを最初から全部読まない。

## 正本

- canonical production: https://boothitemmanager.pages.dev/
- 公開UIのsource: `index.html`
- Cloudflare Pages / GitHub Pages共通build: `build_static.sh`
- Python library: `src/boothitemmanager2/`
- 実行・生成処理: `scripts/`
- test: `tests/`
- browser metadata: `api/metadata.json`
- catalog shard一覧・件数: `api/v1/shards.json` と `api/v1/manifest.json`
- catalog本体: `api/catalog_summary_part*.json`
- `dist/` はbuild生成物。直接編集しない。

## コンテキストを節約する読み方

1. まずこの`AGENTS.md`と対象ファイルだけを読む。
2. catalog全体を知るために`api/catalog_summary_part*.json`や`api/details/*`を全件読み込まない。最初に`api/v1/manifest.json`、`api/v1/shards.json`、`api/metadata.json`を見る。
3. 実データ確認が必要な場合だけ、対象ID・対象shard・必要な行へ絞る。
4. UI変更では`index.html`全体を読み直す前に、対象要素・関数名を検索して必要な範囲だけ読む。
5. `dist/`、Actions artifact、過去commitをsourceの代わりにしない。現在branchのsourceと生成規則を優先する。
6. 同じ処理を別scriptやTaskへ複製しない。`task build`もCIも`build_static.sh`を使う。

## 開発ルール

- 未使用コード、古い説明、重複処理、不要なwrapperを削除する。
- 失敗をfallback、`|| true`、例外握り潰し、根拠のないdefaultで成功扱いしない。
- browser runtimeのcatalog正本はJSONだけ。`window.BOOTH_METADATA`や`window.BOOTH_CATALOG_PART*`のJS fallbackを作らない。
- ルートへPythonファイルを追加しない。libraryは`src/boothitemmanager2/`、実行scriptは`scripts/`、testは`tests/`へ置く。
- 販売者記載の事実、観測値、派生データ、不明値を混同しない。詳細は`README.md`の現在の契約に従う。
- READMEの1行目はcanonical production URLを装飾なしの完全なURLで置く。
- `rel="canonical"`、`robots.txt`、`sitemap.xml`はcanonical production hostへ統一する。

## Commands

- Build: `task build`
- Test: `task test`
- Lint, format, and test: `task check`
- Local preview: `task serve` (`http://localhost:8080`)

変更は、最小の関連test → `task check` → PR → exact-head CI → merge → main read-back → 公開runtime確認まで進める。CI成功だけをproduction成功としない。
