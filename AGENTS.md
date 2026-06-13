# 🌸 エージェントさん向け開発ガイドだょ！ 🌸

このリポジトリで作業するAIエージェントさん（あなただよっ！）のための、かんたんで強力な開発ガイドだもん☆(⑅•ᴗ•⑅)

## 🎀 絶対に守るお約束 (Axioms)
- **Zero-Fat**: むだなコードやコメント、おまもり用のtry-catchは全部パージ（排除）してね！
- **Crash-Driven**: エラーは隠さないで、バグがあったらすぐにクラッシュさせて根本から直すの！
- **Pythonファイルの配置**: ルートには絶対にPythonファイルを置いちゃダメだよぉ！[docs/ARCHITECTURE_LAW.md](file:///home/kafka/projects/boothitemmanager/docs/ARCHITECTURE_LAW.md) に従い、`src/boothitemmanager2/` か `scripts/` に置いてね！

## 🐾 よく使うコマンド (Commands)
Taskfileがあるから、以下のコマンドでいろんなことができるよぉ！

- **ビルド（パイプライン実行）**: `task build`
- **テスト実行**: `task test`
- **コード整形＆静的解析**: `task check`
- **ローカルでプレビュー**: `task serve` (http://localhost:8080)

## 🍭 困ったときは？
- オントロジー（知識）の進化やクリーンアップは [booth-item-management](file:///home/kafka/projects/boothitemmanager/.agents/skills/booth-item-management/SKILL.md) スキルを使ってね！
- Webフロントエンドの改善は [modern-web-guidance](file:///home/kafka/projects/boothitemmanager/.agents/skills/modern-web-guidance/SKILL.md) に従うんだもん✨
