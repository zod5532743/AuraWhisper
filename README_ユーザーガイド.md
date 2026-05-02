# AuraWhisper v1.1.0 ユーザーガイド

## 概要

AuraWhisper は、AI 搭載の高度なダイクテーションツールです。Ollama、Gemini、OpenAI など複数の AI エンジンをサポートし、正確な音声文字起こしを実現します。

---

## 起動方法

### インストーラーから起動
1. `aurawhisper Setup 1.1.0.exe` を実行
2. インストール手順に従う
3. スタートメニューから起動

### ポータブル版から起動
1. `win-unpacked/aurawhisper.exe` を直接実行
2. 設定は `dist/win-unpacked/config.json` に保存されます

---

## 基本操作

### 音声入力
1. **マイを選択**: メインメニューから音声入力をオン
2. **トランスクリプション**: 音声を入力するとリアルタイムで文字起こし
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

### ✨ v1.1.0 新機能

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
- API キーを隠すオプション（Ollama 選択時）
- ダークモード対応
- 洗練されたデザイン

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
2. **Alt+Shift+S** で設定画面を開く
3. 以下の項目を設定：
   - AI Provider（Ollama 推奨）
   - Model Size（7B または 8B）
   - Compute Device（GPU なら選択）
   - マイクロフォン選択
4. **保存**

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
{
  "word": "synonym",
  "meaning": "意味の説明",
  "context": "使用文脈"
}
```

---

## サポート

- **リリースノート**: `RELEASE_NOTES_v1.1.0.md`
- **配布物**: `dist/` フォルダ
- **ドキュメント**: `ui/` フォルダ

---

**バージョン**: 1.1.0  
**開発者**: Antigravity  
**リリース日**: 2026 年 4 月
