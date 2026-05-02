# 起動手順

## 必要なもの

### 1. Python 依存パッケージ

```bash
pip install -r requirements.txt
# または既にインストール済み
pip list | findstr "faster-whisper ollama requests"
```

### 2. Whisper モデル（必須）

```bash
# 音声認識モデルをダウンロード
python backend/run.py download-models
# または手動で HuggingFace からダウンロード
```

### 3. Ollama（オプション - AI 機能を有効にする場合）

```bash
# Ollama をインストール
# https://ollama.ai/download

# モデルをダウンロード
ollama pull llama3.2
ollama pull nemo

# サーバーを起動（バックグラウンド）
ollama serve &
```

### 4. ComfyUI（オプション - 画像生成を有効にする場合）

```bash
# ComfyUI を起動
# https://github.com/comfyanifi/ComfyUI

cd ..\ComfyUI
python main.py
# または ComfyUI Manager を使用して Custom Nodes をインストール
```

## 起動方法

### オフラインモード（推奨）

```bash
# 基本的な起動
python backend/server.py --offline

# 詳細なログ出力
python backend/server.py --offline --debug

# 指定されたポートで起動
python backend/server.py --offline --port 8080

# ブラウザを自動起動（Gradio 画面表示用）
python backend/server.py --offline --open-browser
```

### Ollama + ComfyUI 統合モード

```bash
# Ollama と ComfyUI が動作している状態で起動
python backend/server.py --offline

# config.json を使用
# use_ollama: true
# comfyui_api_url: "http://localhost:8188"
```

### デバッグモード

```bash
# 全機能の動作確認
python backend/server.py --offline --debug

# 音声認識のみテスト
python backend/run.py test-audio

# Ollama 接続テスト
python backend/run.py check-ollama

# ComfyUI 接続テスト
python backend/run.py check-comfyui
```

## 設定

### config.json

```json
{
  "offline_mode": true,
  "use_ollama": true,
  "ollama_model": "llama3.2",
  "ollama_base_url": "http://localhost:11434",
  "device": "cpu",
  "model_size": "small",
  "comfyui_api_url": "http://localhost:8188",
  "comfyui_workflow": "default"
}
```

## 確認項目

起動前に確認すべき項目：

- [ ] Python がインストールされているか
- [ ] 必要な依存パッケージがインストールされているか
- [ ] Whisper モデルがダウンロードされているか（約 1GB）
- [ ] Ollama が動作しているか（AI 機能の場合）
- [ ] ComfyUI が動作しているか（画像生成機能の場合）
- [ ] 適切なポート（デフォルト 8240）が空いているか

## トラブルシューティング

### Whisper モデルが未ダウンロード

```bash
python backend/run.py download-models
```

### Ollama 接続エラー

```bash
# Ollama を起動
ollama serve

# モデルを確保
ollama pull llama3.2
```

### ComfyUI 接続エラー

```bash
cd ..\ComfyUI
python main.py
```
