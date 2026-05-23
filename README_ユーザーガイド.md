# AuraWhisper v1.2.10 ユーザーガイド

## 概要

AuraWhisper は、AI 搭載の高度なダイクテーションツールです。Ollama、Gemini、OpenAI など複数の AI エンジンをサポートし、正確な音声文字起こしを実現します。

---

## 起動方法

### インストーラーから起動
1. `aurawhisper Setup 1.2.10.exe` を実行
2. インストール手順に従う
3. スタートメニューから起動

### ポータブル版から起動
1. `win-unpacked/aurawhisper.exe` を直接実行
2. 設定は `dist/win-unpacked/config.json` に保存されます

---

## 基本操作

### 音声入力
1. **マイクを選択**: 設定メニューから入力デバイスを選択
2. **リアルタイム文字起こし**: 音声を入力すると「操作パネルの上」に浮遊する吹き出し窓に、リアルタイムで次々と文字が表示されます
3. **編集**: 生成されたテキストを直接編集可能
4. **音声出力**: テキストを音声として再生

### ショートカットキー
- **Alt+Shift+S**: 設定画面を開く
- **音声入力開始**: アプリ起動後自動的に開始

### AI プロバイダー選択
1. 設定画面 (Alt+Shift+S) を開く
2. **AI Provider** から選択：
   - **Ollama**: ローカル GPU 推奨
   - **Gemini**: Google AI
   - **OpenAI**: API キー必須
3. 選択したプロバイダーに切り替える

### モデル設定
- **Model Size**: 
  - `7B`: 高速（8GB GPU 推奨）
  - `8B`: バランス
  - `405B`: 高精度（高スぺック推奨）
- **Compute Device**: CPU/GPU を選択

---

## 機能一覧

### ✨ v1.2.0 新機能

#### 🎛️ ダッシュボード
- 現在のステータス表示
- 音声レベルメーター
- 使用 AI モデル情報
- 単語数・文字数表示

#### 📚 文脈 AI 機能
- 前の会話履歴を考慮したトランスクリプション
- 前後の単語を補完
- 自然な文章構成

#### 🔤 標準・IT 用語辞書
- 日本語辞書 (`standard_vocabulary.json`)
- IT 用語辞書 (`it_vocabulary.json`)
- 個別に辞書ファイルをカスタマイズ

#### 🎯 プレミアム UI
- **リアルタイム吹き出しオーバーレイ**: 認識中の文字を半透明の美しいデザインでリアルタイム表示。
- **ウィンドウ座標記憶**: 好きな場所に配置すれば、次回起動時も同じ位置でスタート。
- **ダークモード・グラスモーフィズム対応**: 洗練されたデスクトップ統合デザイン。

---

## 設定項目 (Alt+Shift+S)

### General Settings
- **Global Hotkey**: 音声入力ショートカットの設定

### AI Provider Settings
- **Provider**: AI エンジン選択
- **API Key**: OpenAI/Gemini 用のキー入力

### Model Settings
- **Model Size**: モデルサイズ選択
- **Compute Device**: CPU/GPU 選択

### Transcription Settings
- **Auto Punctuation**: 自動句読点追加
- **Notifications**: 通知の有効/無効

### Device Settings
- **Microphone**: 入力マイ選択

### Vocabulary Settings
- **Import**: 辞書ファイルの読み込み
- **Export**: カスタム辞書の保存

### Maintenance Tools
- **Config Folder**: 設定フォルダを開く
- **Reveal in Explorer**: 設定ファイルを閲覧

---

## 初回起動時の設定

1. アプリを起動
2. バックエンド環境（Python仮想環境）が未構築の場合、自動的に設定画面が開きます。手動で開く場合は Alt+Shift+S を押してください。
3. ご利用のグラフィックボード（GPU）のメーカーに合わせて、設定画面の Engine Setup から適切なエンジンを選択して「Install」をクリックしてください：
   - NVIDIA製グラフィックボード（GeForce、RTX等）をご使用の場合：「Install GPU Engine (CUDA)」を選択します。GPUをフルに活用して最も高速に文字起こしが行えます。
   - AMD製グラフィックボード（Radeon等）をご使用の場合：「Install GPU Engine (AMD DirectML)」を選択します。DirectML技術を利用してAMD GPUで高速動作します。
   - グラフィックボードを搭載していない場合、または動作が不安定な場合：「Install Standard Engine (CPU)」を選択します。CPUで安全に動作します。
4. セットアップ完了後、設定画面でマイクロフォンなどの必要項目を整えて「保存」をクリックします。

---

## よくある質問

### Q: 音声が入力されない
**A**: 設定画面でマイクロフォンを選択してください。

### Q: トランスクリプションが遅い
**A**: 
1. Compute Device を GPU に変更
2. Model Size を小さく（7B）

### Q: API キーが不要
**A**: Ollama を選択すると API キー欄が消えます

### Q: ダッシュボードが表示されない
**A**: `dashboard.js` が正常に読み込まれているか確認してください

### Q: AMD製のGPU（Radeonなど）をご使用の場合、どのエンジンを選択すればよいですか。
**A**: AuraWhisperはDirectML技術を介したAMD製GPUの高速動作に対応しています。AMD製のGPU（Radeon等）を搭載している場合は、セットアップ画面で「Install GPU Engine (AMD DirectML)」を選択してインストールを行ってください。これにより、AMD製GPUのグラフィック処理能力を利用した高速な文字起こしが有効になります。

### Q: 「Install Standard Engine」を押すと、20%（venvの作成）付近で「アクセスが拒否されました (WinError 5)」というエラーで止まります。
**A**: AuraWhisperが「C:\Program Files」の中にインストールされていることが原因です。Program Filesフォルダ内はWindowsのセキュリティにより書き込みが制限されているため、仮想環境（venv）の作成に失敗します。
解決するには、一度AuraWhisperを完全に終了し、「C:\Program Files\aurawhisper」フォルダを丸ごと「デスクトップ」や「マイドキュメント」などの書き込み制限のない一般フォルダにコピーし、そこにある「aurawhisper.exe」を通常通りダブルクリックして起動した状態でセットアップを行ってください（管理者として実行する必要はありません）。

### Q: アプリを「管理者として実行」で起動すると、「Python Not Found」と表示されてアプリが起動しなくなりました。
**A**: 通常通りにインストールしたPythonは、インストールした一般ユーザーの個人環境にのみ登録されます。アプリを「管理者として実行」すると、管理者用の別の環境を探すため、一般ユーザー用にインストールされたPythonを見つけることができなくなります。
解決するには、Pythonのインストーラーを再度実行し、アンインストールした後に再インストールを行います。その際、「Customize installation」を選び、「Advanced Options」画面で「Install for all users（すべてのユーザー用にインストール）」にチェックを入れることで、システム全体（管理者含む）にPythonが登録され、エラーが出なくなります。また、前述の「Program Files以外の場所にフォルダを移動して通常起動する」ことでもこのエラーを完全に回避できます。

### Q: Pythonをインストールしたはずなのに、「Global Python is not found (10%)」というエラーが消えません。
**A**: Pythonのインストール時に、WindowsにPythonの場所を教える設定（環境変数への登録）が漏れている可能性が非常に高いです。
解決するには、Python 3.11.6のインストーラー（python-3.11.6-amd64.exe）を起動し、一度アンインストールした後に再インストールを行ってください。その際、最初の画面の最下部にある「Add Python.exe to PATH」に必ずチェックを入れ、さらに「Customize installation」を進めた先の「Advanced Options」画面にある「Add Python to environment variables（Pythonを環境変数に追加する）」にも必ずチェックを入れてインストールを完了させてください。その後、パソコンを一度再起動するとWindows全体に設定が確実に反映されます。

---

## トラブルシューティング

### アプリが起動しない
1. `dist/win-unpacked/backend` フォルダが存在するか確認
2. Python 3.14 と依存パッケージがインストールされているか確認
3. ファイアウォールで 8240 ポートがブロックされていないか確認

### 設定が反映されない
1. 設定画面を開く (Alt+Shift+S)
2. 各項目を再設定
3. **保存** をクリック
4. アプリを再起動

### バックエンドの自動更新が必要
1. `backend/` フォルダを `dist/win-unpacked/backend` にコピー
2. 再起動

---

## 辞書の使用方法

### 標準辞書の使用
1. 設定画面を開く
2. **Vocabulary** タブを選択
3. **Load Default** をクリック

### カスタム辞書の作成
1. `standard_vocabulary.json` をコピー
2. 追加する単語を追加
3. **Import** で読み込み

### 辞書の形式
```json
[
  {
    "original": "オーラウィスパー",
    "replacement": "AuraWhisper"
  },
  {
    "original": "ジェイソン",
    "replacement": "JSON"
  }
]
```

---

## サポート

- **リリースノート**: `RELEASE_NOTES_v1.2.0.md`
- **配布物**: `dist/` フォルダ
- **ドキュメント**: `ui/` フォルダ

---

**バージョン**: 1.2.10  
**開発者**: Antigravity  
**リリース日**: 2026 年 5 月
