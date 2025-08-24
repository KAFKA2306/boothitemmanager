# tasks.md — BoothList MVP タスク計画

## 0. 概要
- 目的: BOOTH購入資産を正規化し、セット商品を再帰的に分解（深さ1）して、検索・集計・可視化できる最小プロダクト（MVP）を構築する。
- 主要成果物: catalog.yml（正規化カタログ）、metrics.yml（集計）、index.html（静的SPAダッシュボード）。
- 基本方針: 公開ページのスクレイピング＋キャッシュ。セット商品の“対象アバター単位”の仮想サブアイテムを生成。

***

## 1. スコープ（MVP）
- 入力正規化（.input/ のテキスト/CSV/YAML → 内部モデル）
- メタ取得（商品名・ショップ名・価格・画像・URL等）＋単層キャッシュ
- セット商品の再帰分解（深さ1、本文/ファイル名/関連itemリンクのヒューリスティクス）
- 正規化（Item/Variant/Avatar/FileAsset）とエイリアス統合
- 集計（Avatar×Costume 組合せ、件数/合計/平均/中央値）
- 出力（catalog.yml / metrics.yml / index.html）

非スコープ（MVP外）
- ログインAPI、購入価格の厳密復元、再帰深さ2、複合ランキング、関係グラフ可視化、Zip内ディレクトリ解析、マルチレベルキャッシュ

***

## 3. タスク一覧（DoD/依存関係つき）

### M1: ETL基盤とカタログ最小実装
1) リポジトリ整備
- tasks
  - ディレクトリ設計: src/boothlist/, input/, docs/, cache/, dist/
  - 依存管理（pyproject.toml or requirements.txt）
  - サンプル入力配置: input/booth.md, input/booth2.md（生データ）
- DoD
  - 開発環境セットアップ手順がREADMEに記載
  - サンプル入力が存在し、CIでlint/format実行可
- deps: なし

2) 入力正規化モジュール
- tasks
  - URL→item_id抽出（items/(\d+)）ユーティリティ
  - .md/.csv/.yml からの読み込み→内部モデル（RawItem）へ
  - 欠損/重複チェック、基本バリデーション
- DoD
  - 単体テスト（境界ケース: ロケール別URL、短縮URL、混在行）
  - 正規化済みデータがPython dict/listで得られる
- deps: 1)

3) メタ取得器（スクレイピング）＋単層キャッシュ
- tasks
  - 商品ページ取得、複数セレクタのフォールバック抽出（name/shop/price/image/url/creator_id）
  - 1 req/sec のレート制御
  - JSON/YAMLのディスクキャッシュ（キャッシュヒット時はHTTP回避、失敗時もスタブ保存）
- DoD
  - 連続100件でエラーなく完走（失敗時はスタブにフォールバック）
  - 同一item_idの再実行でHTTP回数が著しく減少
- deps: 2)

4) 正規化スキーマ＆catalog.yml 最小出力
- tasks
  - Item/Avatar/FileAssetのデータ構造
  - アバター辞書（Selestia, Kikyo, Kanae, Shinano, Manuka, Moe, Rurune, Hakka, Mizuki 等）のエイリアス統合
  - catalog.yml 出力（variantsはまだ空）
- DoD
  - catalog.yml が生成され、最低限のメタ（name/shop/price/image/url）が入る
  - アバター辞書の単体テスト（エイリアス→正規化コード）
- deps: 3)

5) テスト／品質
- tasks
  - URL抽出、メタ抽出、正規化のユニットテスト
  - 簡易CI（lint+tests）
- DoD
  - テスト合格、カバレッジ閾値（例: 70%）を満たす
- deps: 2)〜4)

### M2: セット分解（深さ1）と集計
6) セット分解ヒューリスティクス（深さ1）
- tasks
  - ファイル名パターン: ^(Kikyo|Selestia|Kanae|Shinano|…)_ / _Kikyo / _Selestia
  - 本文解析: 「対応アバター: …」列挙、"for Selestia" / "Kikyo用" など文脈マッチ
  - 関連item_id抽出: 本文内URLの items/\d+ を収集→子（深さ1）も本文解析（再帰しない）
  - 信頼度スコアリング（filename:0.9 / 明示:0.95 / 文脈:0.8）→0.75未満は破棄
  - 重複統合（avatar_code単位）
- DoD
  - Marshmallow等のフルセットで、Kikyo/Selestia/Kanae…のvariantsが生成される
  - 循環検知（visited）で無限ループを起こさない
- deps: 4)

7) 仮想サブアイテムID生成とcatalog.yml統合
- tasks
  - subitem_id = "{parent}#variant:{avatar_code}:{slug(variant_name)}"
  - parent_itemにvariants配列を追加（targets, files の絞り込み）
- DoD
  - catalog.ymlにvariantsが含まれ、親行から展開できる
- deps: 6)

8) 集計器（metrics.yml）
- tasks
  - Avatar×Costume組合せ: count/total/avg/median（価格はcurrent_price優先、なければwish_price）
  - タイプ別/ショップ別/アバター別の件数サマリ
- DoD
  - metrics.yml が生成され、数値が妥当（サンプルで目視確認）
- deps: 7)

9) データ検証とログ
- tasks
  - 重複item_id、孤立variant、必須メタ欠損の検知と警告
  - スクレイピング失敗・タイムアウトのログ化
- DoD
  - 検証レポート（errors/warnings/stats）が出力される
- deps: 7) 8)

### M3: ダッシュボード（静的SPA）と公開
10) 静的SPA（index.html）
- tasks
  - catalog.yml / metrics.yml をFetchしてクライアント描画
  - 検索（商品名/ショップ/アバター/タイプ/タグ）、フィルタ（type, avatars, shops, price, updated_at）
  - テーブル（サムネ・商品名・ショップ・タイプ・対象アバター・価格・リンク）
  - 親→variants の折りたたみ展開
- DoD
  - ブラウザで即時検索/フィルタが1秒以内で応答
- deps: 8)

11) 公開フローと配布物
- tasks
  - dist/ に catalog.yml / metrics.yml / index.html を配置
  - 簡易自動化スクリプト（buildコマンド）と公開手順書
- DoD
  - ローカルで dist/ を開けば動作、公開手順がREADMEに記載
- deps: 10)

12) 結合テスト・受け入れ
- tasks
  - 入力→正規化→メタ→分解→catalog.yml/metrics.yml→index.html の一連確認
  - 受け入れ基準（フィルタ可、variants展開可、組合せランキング表示）
- DoD
  - 受け入れ基準を満たし、既知セット（例: Marshmallow）で期待通りのvariants表示

***

## 4. 実装ガイド（抜粋）
- レート制御: 約1 req/sec（sleep 1.0）
- キャッシュ: JSON/YAMLで item_id → メタ情報を保存（エラー時スタブ保持）
- スラッグ化: subitem_id用のvariant_slugはASCII簡易変換（MVPはASCII統一）

***

## 5. 受け入れ基準（MVP）
- catalog.yml と metrics.yml が生成される
- セット商品の内訳がvariantsとして展開され、対象アバターでフィルタ可能
- ダッシュボードの検索/フィルタ/並び替え応答が1秒以内

***

## 6. リスクと対応
- スクレイピングDOM変更: セレクタ多重フォールバック＋キャッシュで緩和
- ファイル名規則の揺れ: 辞書拡張と手動YAML上書きで補正（MVP後に対応強化）

***

## 7. バックログ（MVP後）
- GitHub Actionsによる定期更新

***

## 8. 作業ルール
- コーディング規約: Black/ruff等のformatter/linterを使用
- テスト: 単体＋結合。新規ロジックは最小限のユニットテストを添付
- ログ/例外: 期待可能な失敗は例外化せず警告＋継続（レポート出力）

***

## 9. 想定ファイル構成（提案）
- src/boothlist/
  - input_loader.py（md/csv/yml取込・正規化）
  - scrape.py（メタ取得・レート制御・キャッシュ）
  - extract.py（セット分解：本文/ファイル名/関連item）
  - normalize.py（スキーマ整形・エイリアス統合）
  - aggregate.py（metrics生成）
  - export.py（catalog.yml/metrics.yml出力）
- scripts/build.py（ETL一括実行）
- cache/booth_item_cache.yml（キャッシュ）
- dist/index.html, catalog.yml, metrics.yml
- docs/design.md, docs/requirements.md, docs/tasks.md

***

## 10. 作業チケット雛形（例）
- [M1-02] 入力正規化（md/csv/yml）実装
  - 目的: 入力を内部モデルに正規化
  - 成果物: 正規化関数、単体テスト
  - DoD: サンプル入力で期待件数を出力、テスト合格
- [M2-06] セット分解（深さ1）実装
  - 目的: ファイル名/本文/関連itemからvariants抽出
  - 成果物: variants配列、subitem_id生成
  - DoD: 代表セットでKikyo/Selestia等が抽出される