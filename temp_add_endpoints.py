"""server.pyに新しいAPIエンドポイントを挿入するスクリプト"""

file_path = r'd:\VSCODE\AuraWhisper\backend\server.py'

# エンコーディングを自動検出
with open(file_path, 'rb') as f:
    raw = f.read()

# UTF-8 BOMチェック
if raw.startswith(b'\xef\xbb\xbf'):
    content = raw[3:].decode('utf-8')
    encoding = 'utf-8-sig'
else:
    try:
        content = raw.decode('utf-8')
        encoding = 'utf-8'
    except UnicodeDecodeError:
        content = raw.decode('cp932')
        encoding = 'cp932'

# 挿入する新しいコード
new_code = '''

# ========== Dashboard 用 API エンドポイント ==========

@app.post("/history/clear")
async def clear_history():
    """全履歴を削除"""
    save_history([])
    return {"status": "ok"}


@app.post("/config/reset")
async def reset_config():
    """設定をデフォルト値にリセット"""
    global config
    default_config = {
        "hotkey": "Alt+Shift+S",
        "mode": "toggle",
        "language": "ja",
        "model_size": "small",
        "device": "auto",
        "use_ollama": False,
        "ollama_model": "gemma2:2b",
        "window_style": "classic",
        "ai_provider": "lmstudio",
        "ollama_base_url": "http://localhost:1234/v1"
    }
    save_config_file(default_config)
    config = load_config()
    return {"status": "ok"}

'''

# 挿入位置を検索
target = '@app.get("/ollama/models")'
if target in content:
    content = content.replace(target, new_code + target)
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)
    print(f"成功: {file_path} にエンドポイントを挿入しました")
    print(f"エンコーディング: {encoding}")
else:
    print(f"エラー: 対象のテキスト '{target}' が見つかりませんでした")
