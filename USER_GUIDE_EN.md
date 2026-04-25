# AuraWhisper User Guide

Thank you for choosing AuraWhisper. This tool is a premium voice input assistant for Windows that leverages the power of AI to transform your voice into high-quality text.

---

## 1. Startup and Preparation
 
AuraWhisper runs AI locally on your PC to ensure 100% privacy. The following one-time preparation is required:
 
1.  **Install Python**:
    *   Download and install Python 3.10+ from [python.org](https://www.python.org/downloads/).
    *   **Crucial**: Check the box **"Add Python to PATH"** during installation.
2.  **Launch the App**: 
    *   Run `AuraWhisper.exe` from the extracted folder.
3.  **Verify Readiness**: A floating bar will appear. After a few seconds, a notification saying "AI Engine is ready!" will appear.

## 2. Basic Usage

1.  **Start Recording**: Press `Alt + Shift + S` (default hotkey).
    *   The bar will glow red, and the waveform will start moving.
2.  **Speak**: Talk naturally into your microphone.
3.  **Stop Recording**: Press `Alt + Shift + S` again.
4.  **Auto-Insertion**: Once the analysis is complete, the AI-refined text will be automatically pasted at your current cursor position in any app (Notepad, Browser, etc.).

## 3. Floating Bar Interface

*   **Mode Badge (Top Left)**: Displays the current refinement style. Click it to quickly switch between modes like "Translate" or "Summary."
*   **AI ON / OFF (Center)**:
    *   **ON (Blue)**: AI will automatically polish and refine your transcribed text before pasting.
    *   **OFF (Gray)**: Pastes the raw transcription exactly as spoken.
*   **Gear Icon (Right)**: Opens the detailed Settings Dashboard.
*   **Move**: Drag any empty space on the bar to reposition it anywhere on your screen.

## 4. Advanced Settings

Click the gear icon to access the Settings Dashboard:

*   **Dashboard**: View your total character count and estimated time saved.
*   **History**: Review and reuse your past transcriptions.
*   **Vocabulary**: Register technical terms or custom names to prevent AI misinterpretations.
*   **General**: Change the global hotkey or enable "Run at Startup."

## 5. Premium Features (Ollama)

To maximize the "AI ON" refinement, we recommend installing the free AI engine **Ollama**.
1.  Download and install from [ollama.com](https://ollama.com/).
2.  Go to Settings ➔ AI Engine and install a model (e.g., `gemma2:2b`).
3.  This enables ultra-fast, local AI refinement while keeping your data 100% private on your own PC.

---

## Troubleshooting

*   **No Response**: Go to Settings ➔ General ➔ "Force Reboot" to restart the app.
*   **UI Issues**: Try moving the window or restarting the application.

---
© 2026 AuraWhisper Project.
