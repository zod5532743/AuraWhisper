# UltraWhisper Project Handover

## 📋 Project Overview
UltraWhisper is a hybrid application designed for real-time audio transcription and automated text processing (refinement) using AI. It captures audio via a microphone, transcribes it using OpenAI's Whisper model, optionally refines the text using Ollama (LLM), and automatically pastes the final result into the active window using keyboard simulation.

## 🏗️ Architecture & Tech Stack
The project uses a dual-process architecture:

### 1. Frontend (Electron)
- **Role:** User Interface (UI), Global Hotkey management, and process orchestration.
- **Tech Stack:** Electron, JavaScript (Node.js), HTML/CSS.
 
### 2. Backend (Python FastAPI)
- **Role:** Heavy-duty processing (Audio Recording, Whisper Transcription, Ollm-based Text Refinement, Clipboard/Keyboard Interaction).
- **Tech Stack:** Python, FastAPI, Whisper (via `faster-whisper`), NumPy, SciPy, `sounddevice`, `pynput`, `pyperclip`.

## 🛠️ Core Workflow
1. **Trigger:** User presses a registered global hotkey (e.g., `Shift+F1`).
2. **Recording:** The Python backend starts recording audio from the specified `device_index` using `sounddevice`.
3. **Processing:** Upon releasing the hotkey, the backend stops recording, saves a `.wav` file, and runs the transcription process.
4. **Refinement (Optional):** If `use_ollama` is `true`, the transcribed text is sent to an Ollama endpoint for grammar correction/refinement.
5. **Output:** The final text is copied to the system clipboard and `Ctrl+V` is simulated in the active window.

## ⚙️ Key Configuration (`config.json`)
The behavior of the system is### 既知の課題と解決策 (2026-04-20 更新)

*   **ウィンドウ判定と貼り付けの失敗**:
    *   **原因**: 録音開始時にレコーダーがフォーカスを奪うと、元のアプリを見失う。
    *   **対策**: `mainWindow` に `focusable: false` を設定し、`showInactive()` を使用することで、フォーカス移動を物理的に遮断。貼り付け時は `AttachThreadInput` を使用して強制的に前面化する。
*   **バックエンドの突然のクラッシュ**:
    *   **原因**: Windows + CPU環境で `faster-whisper` が `int8` 演算を行うと、稀にアクセス違反 (Code 3221225477) が起きる。
    *   **対策**: `compute_type` を `float32` に設定して安定性を優先。万が一のために `main.js` でプロセスの自動再起動ロジックを実装。
*   **マイクが音を拾わない**:
    *   **対策**: `sounddevice` で取得される ID は MME/WASAPI などで重複するため、Mixing Driver (ID: 1 など) を設定画面から正しく選択する必要がある。
*   **波形が表示されない**:
    *   **対策**: Canvas の `z-index` を最前面に設定。音量レベルを標準 `float` に変換してJSON送信することでシリアライズエラーを回避。
ing `debug_audio.py`).
- `use_ollama`: Boolean to enable/disable LLM-based text refinement.
- `mode`: `toggle` (press once to start/stop) or `hold` (press and hold).

## 🔍 Recent Debugging & Known Issues
- **Audio Device Mismatch:** The default `device_index: 0` (Sound Mapper) may not capture audio. It is recommended to use the System Settings UI to select physical hardware like `US-2x2` or `NVIDIA Broadcast`.
- **Backend Connection (ECONNREFUSED):** If "Offline" persists, check if the Python backend crashed due to model downloading. Forcing a lighter model like `tiny` in `config.json` resolves this initial latency.
- **Path Encoding Issue:** On Windows, non-ASCII characters in paths (e.g., `繝槭う繝峨Λ繧､繝`) may appear in logs but usually don't block execution if `venv` path is absolute.
- **Model Loading Latency:** When using `medium` or `large` models, the Python backend may appear "offline" or "unresponsive" in the Electron UI during the initial loading phase. The UI will update to "Ready" once `Transcriber initialized successfully` appears in the logs.

- **Python Version Compatibility:** Current testing performed on Python 3.14. Be cautious of potential `access violation` errors in `faster-whisper` due to very new Python versions.

## ✨ Latest Updates (2026-04-19)
### 1. Extended Settings UI
- Added controls for **Whisper Model Size** (`tiny` to `large-v3`).
- Added **Recognition Language** selection (`ja`, `en`).
- Added **Ollama Model Name** input field for customized text refinement.
- Dynamic visibility for Ollama settings based on enabled status.

### 2. Premium UI/UX Redesign
- Implemented **Glassmorphism** design system across the application.
- Unified color palette with deep navy backgrounds and neon blue accents.
- Improved typography using the `Outfit` font and `JetBrains Mono` for code-like elements (hotkeys).
- Added micro-animations: Pulse ring for recording, smooth transitions for setting groups, and button hover effects.
- Expanded settings window to `450x650` for better accessibility.


## 🚀 How to Run
### Manual Start (Development)
```powershell
npm start
```

### Batch Start (Legacy/Convenience)
Use the existing `start.bat` (if configured) to launch the environment.

## 🧪 Testing
- **Unit Tests:** Located in `/tests`. Use `python -m pytest tests/test_audio_recorder.py` to verify audio-related logic.
- **Audio Debugging:** Use the `debug_audio.py` script to verify microphone accessibility.
