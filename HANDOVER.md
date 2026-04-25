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

## 更新履歴 (v1.0.1)
- **リカバリーロジックの安定化**: 
  - バックエンド監視のタイムアウトをしきい値を延長（30秒）。
  - 通信タイムアウトの導入により、モデルロード中の誤作動を防止。
  - プロセス停止時のタイマー競合を解消。

## ビルド・配布手順 (v1.0.1)
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
