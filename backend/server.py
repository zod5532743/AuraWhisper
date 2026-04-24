import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from pydantic import BaseModel
from typing import Optional
import logging
import threading
import time
import pyperclip
import ctypes
from pynput.keyboard import Controller, Key, Listener, KeyCode

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress uvicorn access logs to avoid terminal spam from status polling
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Add NVIDIA DLL directories to path on Windows
if os.name == 'nt':
    venv_site_packages = os.path.join(os.path.dirname(__file__), "venv", "Lib", "site-packages")
    nvidia_base = os.path.join(venv_site_packages, "nvidia")
    if os.path.exists(nvidia_base):
        for root, dirs, files in os.walk(nvidia_base):
            if 'bin' in dirs:
                bin_path = os.path.normpath(os.path.join(root, 'bin'))
                os.add_dll_directory(bin_path)
                os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]

from transcriber import Transcriber
from audio_recorder import AudioRecorder

# Global state and instances

app_state = {
    "is_recording": False,
    "status": "loading",
    "error_message": None
}

user32 = ctypes.windll.user32
target_hwnd = None
keyboard_controller = Controller()
transcriber = None
recorder = None
config = {}
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "history.json")
VOCAB_PATH = os.path.join(os.path.dirname(__file__), "..", "vocabulary.json")
MODES_PATH = os.path.join(os.path.dirname(__file__), "..", "modes.json")

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def save_config_file(new_config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=4, ensure_ascii=False)

def load_history():
    try:
        if not os.path.exists(HISTORY_PATH): return []
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def save_history(data):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_vocabulary():
    try:
        if not os.path.exists(VOCAB_PATH): return []
        with open(VOCAB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def save_vocabulary(data):
    with open(VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_modes():
    try:
        if not os.path.exists(MODES_PATH): return []
        with open(MODES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def save_modes(data):
    with open(MODES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def init_app_globals():
    global config, recorder, transcriber
    config = load_config()
    recorder = AudioRecorder(device_index=config.get("device_index"))
    
    # Initialize history and vocabulary files if they don't exist
    if not os.path.exists(HISTORY_PATH): save_history([])
    if not os.path.exists(VOCAB_PATH): save_vocabulary([])
    if not os.path.exists(MODES_PATH): save_modes([])
    # Transcriber is initialized later in background thread


def init_transcriber_task():
    global transcriber
    try:
        transcriber = Transcriber(
            model_size=config.get("model_size", "small"),
            device=config.get("device", "cpu"),
            compute_type=config.get("compute_type")
        )
        app_state["status"] = "ready"
        app_state["error_message"] = None
        logger.info("Transcriber initialized successfully")
    except Exception as e:
        error_msg = f"Transcriber init error: {str(e)}"
        logger.error(error_msg)
        app_state["status"] = "error"
        app_state["error_message"] = error_msg


# --- Hotkey Configuration Mapping ---
from pynput.keyboard import Key, KeyCode

# Map string representations to pynput Key objects
KEY_MAP = {
    'ctrl': Key.ctrl,
    'control': Key.ctrl,
    'alt': Key.alt,
    'shift': Key.shift,
    'cmd': Key.cmd,
    'command': Key.cmd,
    'win': Key.cmd,
    'enter': Key.enter,
    'space': Key.space,
    'backspace': Key.backspace,
    'tab': Key.tab,
    'esc': Key.esc,
    'delete': Key.delete,
    'capslock': Key.caps_lock,
}
# Add F1-F12 to the map
for i in range(1, 13):
    KEY_MAP[f'f{i}'] = getattr(Key, f'f{i}')

# --- Hotkey Listener Logic ---
active_keys = set()
hotkey_listener = None

def parse_hotkey(hotkey_str):
    """Pars               nse a hotkey string like 'Alt+Shift+S' into a set of pynput keys."""
    if not hotkey_str:
        return set()
    
    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    keys = set()
    for p in parts:
        if p in KEY_MAP:
            keys.add(KEY_MAP[p])
        elif len(p) == 1:
            try:
                keys.add(KeyCode.from_char(p))
            except Exception:
                pass
        else:
            # Fallback for strings that might not be in KEY_MAP but are valid
            # This is a safety net
            pass
    return keys

def on_press(key):
    global config
    if config.get("mode") != "hold": return
    
    target_keys = parse_hotkey(config.get("hotkey", "Alt+Shift+S"))
    
    # Add the pressed key to the set of active keys
    # We normalize the key to handle both Key and KeyCode
    active_keys.add(key)
    
    # Check if all target keys are currently pressed
    # Using issubset for elegant and efficient set comparison
    if target_keys and target_keys.issubset(active_keys):
        if not app_state["is_recording"]:
            logger.info(f"Push-to-Talk Triggered: Start (Keys: {config.get('hotkey')})")
            trigger_start_sync()

def on_release(key):
    global config
    if config.get("mode") != "hold": return
    
    target_keys = parse_hotkey(config.get("hotkey", "Alt+Shift+S"))
    
    # Remove the released key from active_keys
    # We use a list to avoid 'Set size changed during iteration' error
    to_remove = [ak for ak in active_keys if ak == key]
    for r in to_remove:
        active_keys.remove(r)
    
    # If any of the target keys (the ones we care about) are released, stop recording
    if app_state["is_recording"]:
        # Check if the intersection of released target keys and required keys is non-empty
        # Or more simply: if any key in target_keys is no longer in active_keys
        if not target_keys.issubset(active_keys):
            logger.info(f"Push-to-Talk Triggered: Stop (Key Released)")
            trigger_stop_sync()



def trigger_start_sync():
    global target_hwnd
    if transcriber is None or app_state["is_recording"]: return
    
    # Try multiple times to get the correct foreground window 
    # (incase focus is transitioning)
    max_retries = 3
    for _ in range(max_retries):
        hwnd = user32.GetForegroundWindow()
        title_len = user32.GetWindowTextLengthW(hwnd)
        if title_len > 0: # If window has a title, it's likely a real app (not desktop/shell)
            target_hwnd = hwnd
            logger.info(f"Target window captured: HWND={target_hwnd}")
            break
        time.sleep(0.05)
    else:
        target_hwnd = user32.GetForegroundWindow() # Fallback

    recorder.start_recording()
    app_state["is_recording"] = True
    app_state["status"] = "recording"
    app_state["error_message"] = None


def trigger_stop_sync():
    if not app_state["is_recording"]: return
    app_state["is_recording"] = False
    app_state["status"] = "analyzing"
    threading.Thread(target=process_and_paste_task).start()

def process_and_paste_task():
    audio_path = recorder.stop_recording()
    if not audio_path:
        app_state["is_recording"] = False
        app_state["status"] = "ready"
        return
    
    try:
        from datetime import datetime
        start_time = time.time()
        
        raw_text = transcriber.transcribe(audio_path, language=config.get("language", "ja"))
        logger.info(f"Transcription result: [{raw_text}]")
        
        # Apply Vocabulary replacement (Pre-Ollama)
        vocabulary = load_vocabulary()
        for item in vocabulary:
            if item.get("original") and item.get("replacement"):
                raw_text = raw_text.replace(item["original"], item["replacement"])
        
        if config.get("use_ollama", True):
            ollama_url = "http://localhost:11434/api/generate"
            model = config.get("ollama_model", "qwen2.5-coder:14b")
            
            # Get current mode prompt
            active_mode_id = config.get("active_mode_id", "general")
            modes = load_modes()
            active_mode = next((m for m in modes if m["id"] == active_mode_id), None)
            
            if active_mode:
                system_prompt = active_mode.get("prompt", "校正してください。")
                prompt = f"{system_prompt}\n\n入力テキスト:\n{raw_text}"
            else:
                prompt = f"以下の文章を校正して、修正後の文章のみ出力してください:\n{raw_text}"
            
            try:
                with httpx.Client() as client:
                    resp = client.post(ollama_url, json={"model": model, "prompt": prompt, "stream": False}, timeout=30.0)
                    refined_text = resp.json().get("response", raw_text) if resp.status_code == 200 else raw_text
                    logger.info(f"Refined via Ollama (Mode: {active_mode_id}): [{refined_text}]")
            except:
                refined_text = raw_text
        else:
            refined_text = raw_text
        
        # Final cleanup and Smart Insertion
        final_text = refined_text.strip()
        
        if final_text:
            # Auto-Punctuation
            if config.get("auto_punctuation", True):
                punc_marks = (".", "!", "?", "。", "！", "？")
                if not final_text.endswith(punc_marks):
                    if config.get("language") == "ja":
                        final_text += "。"
                    else:
                        final_text += "."
            
            # After Insertion suffix
            after_insert = config.get("after_insertion", "none")
            if after_insert == "newline":
                final_text += "\n"
            elif after_insert == "space":
                final_text += " "

            # Save to History
            duration = time.time() - start_time
            history_item = {
                "id": int(time.time() * 1000),
                "timestamp": datetime.now().isoformat(),
                "model": config.get("ollama_model") if config.get("use_ollama") else config.get("model_size"),
                "original": raw_text,
                "text": final_text,
                "chars": len(final_text),
                "duration": round(duration, 2)
            }
            history = load_history()
            history.insert(0, history_item) # Newest first
            save_history(history[:100]) # Keep last 100
            
            pyperclip.copy(final_text)
            logger.info("Copied to clipboard. Re-focusing and pasting...")
            
            if target_hwnd:
                # Get the thread IDs
                foreground_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
                target_thread = user32.GetWindowThreadProcessId(target_hwnd, None)
                
                # Try to attach thread input to bypass focus restrictions
                if foreground_thread != target_thread:
                    user32.AttachThreadInput(foreground_thread, target_thread, True)
                    user32.SetForegroundWindow(target_hwnd)
                    user32.SetFocus(target_hwnd)
                    user32.AttachThreadInput(foreground_thread, target_thread, False)
                else:
                    user32.SetForegroundWindow(target_hwnd)
                
                time.sleep(1.0) # Slightly longer wait for window to become stable
            
            # Reset all modifiers to prevent interference
            for m_key in [Key.ctrl, Key.shift, Key.alt, Key.cmd]:
                keyboard_controller.release(m_key)
            
            # Send Paste command
            with keyboard_controller.pressed(Key.ctrl):
                keyboard_controller.tap('v')
            
            logger.info("Paste command sent.")

    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error(error_msg)
        app_state["status"] = "error"
        app_state["error_message"] = error_msg
    finally:
        app_state["is_recording"] = False
        if app_state["status"] != "error":
            app_state["status"] = "ready"
        if os.path.exists(audio_path):
            os.remove(audio_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_globals()
    threading.Thread(target=init_transcriber_task).start()
    global hotkey_listener
    hotkey_listener = Listener(on_press=on_press, on_release=on_release)
    hotkey_listener.start()
    yield
    if hotkey_listener:
        hotkey_listener.stop()

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def get_status():
    status = app_state.copy()
    # Explicitly cast to float to avoid numpy JSON serialization error
    status["volume"] = float(recorder.current_volume) if recorder else 0.0
    return status


@app.get("/devices")
async def get_devices():
    devices = AudioRecorder.get_input_devices()
    current_device_id = config.get("device_index")
    for d in devices:
        d["is_selected"] = (d["id"] == current_device_id)
    return devices


@app.get("/config")
async def get_config():
    return load_config()

@app.post("/config")
async def save_config(new_config: dict):
    logger.info(f"Saving new config: {new_config}")
    try:
        save_config_file(new_config)
        global config, recorder
        config = load_config()
        # Update recorder if device changed
        recorder = AudioRecorder(device_index=config.get("device_index"))
        logger.info("Config saved and reloaded successfully")
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start")
async def api_start():
    trigger_start_sync()
    return {"status": "ok"}

@app.post("/stop")
async def api_stop():
    trigger_stop_sync()
    return {"status": "ok"}

@app.get("/history")
async def get_history():
    return load_history()

@app.get("/vocabulary")
async def get_vocabulary():
    return load_vocabulary()

@app.post("/vocabulary")
async def update_vocabulary(payload: dict):
    vocab = load_vocabulary()
    action = payload.get("action")
    if action == "add":
        item = payload.get("item")
        if not item or "original" not in item:
            raise HTTPException(400, "Invalid item")
        vocab.append(item)
    elif action == "delete":
        idx = payload.get("index")
        if idx is not None and 0 <= idx < len(vocab):
            vocab.pop(idx)
    save_vocabulary(vocab)
    return {"status": "ok", "vocabulary": vocab}

@app.get("/modes")
async def get_modes():
    return load_modes()

@app.post("/modes")
async def update_modes(payload: dict):
    modes = load_modes()
    action = payload.get("action")
    if action == "add":
        item = payload.get("item")
        modes.append(item)
    elif action == "delete":
        idx = payload.get("index")
        if idx is not None and 0 <= idx < len(modes):
            modes.pop(idx)
    elif action == "update":
        idx = payload.get("index")
        item = payload.get("item")
        if idx is not None and 0 <= idx < len(modes):
            modes[idx] = item
    save_modes(modes)
    return {"status": "ok", "modes": modes}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
