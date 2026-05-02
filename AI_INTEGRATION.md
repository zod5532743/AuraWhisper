# AuraWhisper AI 統合

## 概要
このドキュメントは、AuraWhisper v1.1.0 における AI 地脈解析機能の統合内容を説明します。

## 依存ライブラリ
```python
# backend.py の追加
import requests, json, os, time

# requirements.txt に追加
ollama>=0.3.3
requests>=2.31.0
```

## システム要件

### Ollama
- [Ollama](https://ollama.ai) 0.1.30+ のインストール
- デフォルトモデル：`gemma2:2b`

### モデルローダー
- CPU 処理：ollama 標準
- GPU 処理（NVIDIA）：なし（CPU 専用）
- 将来：ONNX Runtime GPU サポート検討中

## 設定ファイル

### config.json
```json
{
  "ollama": {
    "model": "gemma2:2b",
    "base_url": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

## API エンドポイント

### GET /api/analyze-aura
地脈データからの AI 解析をリクエストします。

**Request:**
```http
GET /api/analyze-aura
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "analysis": "解析結果テキスト",
    "confidence": 0.85,
    "insights": ["異常検知", "推奨アクション"]
  }
}
```

## Python API サンプル

```python
import requests

response = requests.get('http://localhost:8240/api/analyze-aura',
                        headers={'Authorization': 'Bearer eyJhbG...'})
data = response.json()
print(data['data']['analysis'])
```

## ダッシュボード

ダッシュボード UI（`ui/dashboard.html`）は、以下を可視化します：

1. 最近の地脈強度変化（折れ線グラフ）
2. AI 解析履歴（時間順リスト）
3. 地脈マップの異常箇所マーカー

## トラブルシューティング

### モデルが読み込まれない場合
```bash
ollama pull gemma2:2b
```

### API エンドポイントが返却しない場合
```bash
curl http://localhost:11434/api/tags
```
Ollama が正常に起動しているか確認してください。
