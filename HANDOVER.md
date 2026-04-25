# AuraWhisper 開発完了ドキュメント (2026-04-25)

## 最終ステータス
すべての開発フェーズが完了し、AuraWhisperはプレミアムなローカルAI音声入力ツールとして完成しました。

### 実装済みの全機能
1.  **フェーズ 1 (Dashboard)**: サイドバー付き管理画面、動的な統計表示、チャート統合。
2.  **フェーズ 2 (Memory)**: 履歴の修正前後比較、個別削除、辞書のインライン編集機能。
3.  **フェーズ 3 (Modes)**: 高度なモード管理（手動切替の完全同期、カスタムプロンプト）。
4.  **フェーズ 4 (Automation)**: スマート・インサーションの最適化、プレミアムUIポリッシュ、自動起動の安定化。

## 技術スタック
- **Frontend**: Electron, HTML/CSS/JS (Vanilla), Chart.js
- **Backend**: Python (FastAPI), Faster-Whisper, Ollama API
- **Models**: Qwen 2.5 Coder (14B), Faster-Whisper Large-v3

## 運用上の注意
- バックエンドの安定性のために、設定変更後は `Synchronizing...` と表示され、数秒で準備が整います。
- ショートカットキーが競合する場合は、設定画面から変更して保存してください。

## 更新履歴 (v1.0.2)
- **リカバリーロジックの抜本的強化**: 
  - 監視タイマーの重複を完全に排除し、判定の混線を解消。
  - プロセスの生存確認を導入し、モデルロード中などの高負荷時も最大 80 秒まで待機するように調整。
  - 監視失敗時の詳細ログ（Reason）を出力。
- **軽量化パッケージ (Lightweight Policy)**:
  - Python 環境を同梱せず、ユーザー環境の Python を利用する方針に変更（配布サイズを約 108MB に削減）。
  - `main.js` の起動パスをソース実行用に最適化。

## 更新履歴 (v1.0.3)
- **ポート競合の回避**: 
  - 他社製アプリ（Superwhisper等）との衝突を避けるため、使用ポートを `8000` から `8240` に変更。
- **監視ロジックの再構築**:
  - `setInterval` から再帰的 `setTimeout` に変更し、タイマーの重なりを物理的に防止。
  - プロセス生存時の待機時間を最大 120 秒まで延長。

## ビルド・配布手順 (v1.0.3)
現在の環境制限により `electron-builder` の自動 ZIP 化が失敗するため、手動でパッケージングを行っています。
1.  **Python バックエンドのビルド**:
    `.\backend\venv\Scripts\pyinstaller --onedir --name "server" .\backend\server.py`
2.  **配布フォルダの作成**:
    `dist\win-unpacked` の内容をベースに、`resources\app.asar` を削除し、ソースコードと `server_dist` を `resources\app` および `resources\backend` に配置。
3.  **圧縮**:
    `Compress-Archive` を使用して `dist\AuraWhisper-v1.0.1-Portable.zip` を作成。

## 今後の展望
- モバイルアプリ（リモート録音）との連携。
- マルチ言語の同時翻訳モードの強化。
