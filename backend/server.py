import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from pydantic import BaseModel
from typing import Optional
import logging
import threading
import time
import pyperclip
import ctypes
import queue
import numpy as np
from pynput.keyboard import Controller, Key, Listener, KeyCode

# Setup logging
appdata = os.getenv('APPDATA')
if appdata:
    APP_DATA_DIR = Path(appdata) / "aurawhisper"
else:
    APP_DATA_DIR = Path.home() / ".aurawhisper"

os.makedirs(APP_DATA_DIR, exist_ok=True)

log_file = os.path.join(APP_DATA_DIR, "aurawhisper_backend.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add NVIDIA DLL directories to path on Windows
if os.name == 'nt':
    import sys
    # Search in multiple possible site-packages locations
    possible_paths = []
    # 1. Current sys.path (active Python environment)
    for p in sys.path:
        if "site-packages" in p:
            possible_paths.append(p)
    # 2. Local backend/venv
    possible_paths.append(os.path.join(os.path.dirname(__file__), "venv", "Lib", "site-packages"))
    
    for site_pkg in possible_paths:
        nvidia_base = os.path.join(site_pkg, "nvidia")
        if os.path.exists(nvidia_base):
            logger.info(f"Checking for NVIDIA DLLs in: {nvidia_base}")
            for root, dirs, files in os.walk(nvidia_base):
                if 'bin' in dirs:
                    bin_path = os.path.normpath(os.path.join(root, 'bin'))
                    try:
                        os.add_dll_directory(bin_path)
                        os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]
                        logger.info(f"Added NVIDIA DLL directory: {bin_path}")
                    except Exception as e:
                        logger.warning(f"Failed to add DLL directory {bin_path}: {e}")


    try:
        try:
            from transcriber import Transcriber
            from audio_recorder import AudioRecorder
        except ImportError:
            from .transcriber import Transcriber
            from .audio_recorder import AudioRecorder
        engine_ready = True
    except Exception as e:
        logger.error(f"Engine libraries missing: {e}")
        engine_ready = False
        AudioRecorder = None

# Check for CUDA and DirectML availability
cuda_available = False
dml_available = False
if engine_ready:
    try:
        import ctranslate2
        cuda_available = ctranslate2.get_cuda_device_count() > 0
        logger.info(f"CUDA detected: {cuda_available} (Count: {ctranslate2.get_cuda_device_count()})")
    except Exception as e:
        logger.warning(f"Failed to check CUDA availability: {e}")
        cuda_available = False

    try:
        import onnxruntime as ort
        dml_available = "DmlExecutionProvider" in ort.get_available_providers()
        logger.info(f"DirectML detected: {dml_available} (Available providers: {ort.get_available_providers()})")
    except Exception as e:
        logger.warning(f"Failed to check DirectML availability: {e}")
        dml_available = False

# Global state and instances

app_state = {
    "is_recording": False,
    "status": "loading",
    "status_message": "Initializing...",
    "is_reloading": False,
    "error_message": None,
    "setup_progress": 0,
    "setup_status": "idle", # idle, downloading, installing, finished, error
    "last_ai_check_time": 0.0,
    "last_ai_check_result": False,
    "partial_transcript": ""
}

def check_full_environment():
    """Returns detailed info about current libraries and hardware"""
    info = {
        "engine_ready": engine_ready,
        "cuda_available": cuda_available,
        "dml_available": dml_available,
        "has_whisper": False,
        "has_pynput": False,
        "has_fastapi": True # Obviously
    }
    try:
        import faster_whisper
        info["has_whisper"] = True
    except: pass
    try:
        if not info["has_whisper"]:
            import optimum
            info["has_whisper"] = True
    except: pass
    try:
        import pynput
        info["has_pynput"] = True
    except: pass
    return info

user32 = ctypes.windll.user32
target_hwnd = None
keyboard_controller = Controller()
transcriber = None
recorder = None
config = {}
# Define paths relative to this script
BASE_DIR = Path(__file__).resolve().parent

# If running inside a backend folder, APP_ROOT is parent. 
if BASE_DIR.name == "backend":
    APP_ROOT = BASE_DIR.parent
else:
    APP_ROOT = BASE_DIR

CONFIG_PATH = APP_DATA_DIR / "config.json"
HISTORY_PATH = APP_DATA_DIR / "history.json"
VOCAB_PATH = APP_DATA_DIR / "vocabulary.json"
MODES_PATH = APP_DATA_DIR / "modes.json"
MODELS_DIR = (APP_DATA_DIR / "models").resolve()
TRANSCRIPTIONS_DIR = (APP_DATA_DIR / "transcriptions").resolve()

# Ensure directories exist
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)

# Important for modular distribution: redirect model cache to the models dir
os.environ["HF_HOME"] = str(MODELS_DIR)
os.environ["XDG_CACHE_HOME"] = str(MODELS_DIR)
os.environ["HF_HUB_CACHE"] = str(MODELS_DIR) # Add more specific hub cache env

logger.info(f"App Root initialized at: {APP_ROOT}")
logger.info(f"Config Path: {CONFIG_PATH}")
logger.info(f"Models Directory (Resolved): {MODELS_DIR}")

# Ensure critical files exist with defaults if missing
def ensure_file_exists(path, default_content):
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_content, f, indent=4, ensure_ascii=False)
            logger.info(f"Created default file at: {path}")
        except Exception as e:
            logger.error(f"Failed to create default file {path}: {e}")

ensure_file_exists(CONFIG_PATH, {
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
})
ensure_file_exists(HISTORY_PATH, [])
ensure_file_exists(VOCAB_PATH, [])

logger.info(f"App Root: {APP_ROOT}")
logger.info(f"Config Path: {CONFIG_PATH}")

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
    if not HISTORY_PATH.exists(): return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return []

def save_history(data):
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save history: {e}")

def load_vocabulary():
    if not VOCAB_PATH.exists(): return []
    try:
        with open(VOCAB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading vocabulary: {e}")
        return []

def save_vocabulary(data):
    try:
        with open(VOCAB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save vocabulary: {e}")

DEFAULT_MODES = [
    {
        "id": "general",
        "name": "General",
        "description": "標準的な校正。フィラーを除去し、自然な日本語に整えます。",
        "prompt": "提供されたテキストからフィラー（えー、あの、その等）や不要な言い直しを取り除き、自然な日本語として校正してください。修正後のテキストのみを出力してください。",
        "icon": "home"
    },
    {
        "id": "slack",
        "name": "Slack / Chat",
        "description": "チャット向けの簡潔な表現。フィラーを除去し、テンポを重視します。",
        "prompt": "提供されたテキストからフィラーを除去し、Slackやチャット向けの簡潔でリズムの良い表現に校正してください。修正後のテキストのみを出力してください。",
        "icon": "message-circle"
    },
    {
        "id": "email",
        "name": "Professional Email",
        "description": "丁寧なビジネス敬語。フィラーを除去し、ビジネス文書に整えます。",
        "prompt": "提供されたテキストからフィラーを除去し、ビジネスメールとしてそのまま使える丁寧な敬語表現に書き換えてください。修正後のテキストのみを出力してください。",
        "icon": "mail"
    },
    {
        "id": "summary",
        "name": "Summary",
        "description": "内容を簡潔に要約します。重要なポイントを抽出します。",
        "prompt": "提供されたテキストの内容を理解し、重要なポイントを簡潔に要約してください。要約後のテキストのみを出力してください。",
        "icon": "align-left"
    },
    {
        "id": "translate-en",
        "name": "JP to EN",
        "description": "日本語から英語へ翻訳します。自然な英語表現に変換します。",
        "prompt": "提供された日本語のテキストを、自然で流暢な英語に翻訳してください。翻訳後の英語テキストのみを出力してください。",
        "icon": "globe"
    },
    {
        "id": "bullets",
        "name": "Bullet Points",
        "description": "内容を整理し、箇条書きで構造化します。",
        "prompt": "提供されたテキストからフィラーを取り除き、内容を整理して、重要なポイントを箇条書きで構造化して出力してください。修正後のテキストのみを出力してください。",
        "icon": "list"
    },
    {
        "id": "code",
        "name": "Code Assistant",
        "description": "プログラミングや技術用語に最適化。コードのみ、または技術解説を出力します。",
        "prompt": "提供されたテキストを技術的な文脈で理解し、プログラミングコードが含まれる場合は適切なコードブロックとして出力してください。解説が必要な場合は簡潔に行い、技術用語の綴り（キャメルケース等）を正確に保ってください。修正後のテキストのみを出力してください。",
        "icon": "code"
    },
    {
        "id": "markdown",
        "name": "Markdown Doc",
        "description": "見出しや太字を活用。Markdown形式のドキュメントを作成します。",
        "prompt": "提供されたテキストの内容を整理し、Markdown形式（#で見出し、**で強調等）を使って構造化されたドキュメントとして出力してください。読みやすさを重視し、適切な改行やリストを活用してください。修正後のテキストのみを出力してください。",
        "icon": "type"
    }
]

def load_modes():
    if not MODES_PATH.exists():
        logger.warning(f"Modes file not found at {MODES_PATH}. Using defaults.")
        return DEFAULT_MODES
    try:
        with open(MODES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if data else DEFAULT_MODES
    except Exception as e:
        logger.error(f"Error loading modes: {e}")
        return DEFAULT_MODES

def save_modes(data):
    try:
        with open(MODES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save modes: {e}")

def init_app_globals():
    global config, recorder, transcriber
    config = load_config()
    
    # Resolve device_index based on saved device_name (Task 2)
    saved_device_name = config.get("device_name")
    current_device_index = config.get("device_index")
    
    if saved_device_name and saved_device_name != "System Default":
        if AudioRecorder:
            try:
                devices = AudioRecorder.get_input_devices()
                found = False
                for d in devices:
                    if d.get("name") == saved_device_name:
                        current_device_index = d.get("id")
                        config["device_index"] = current_device_index
                        found = True
                        logger.info(f"Resolved microphone '{saved_device_name}' to index {current_device_index}")
                        break
                if not found:
                    logger.warning(f"Saved microphone '{saved_device_name}' not found. Falling back to default or saved index {current_device_index}")
            except Exception as e:
                logger.error(f"Failed to resolve device name index: {e}")
        else:
            logger.warning("AudioRecorder unavailable; cannot resolve saved microphone name.")
            
    if AudioRecorder:
        recorder = AudioRecorder(device_index=current_device_index)
    else:
        recorder = None
        logger.warning("AudioRecorder unavailable; audio recording disabled.")
    
    # Initialize history and vocabulary files if they don't exist
    if not HISTORY_PATH.exists(): save_history([])
    if not VOCAB_PATH.exists(): save_vocabulary([])
    
    # Ensure modes are initialized with defaults if file is missing or empty
    if not MODES_PATH.exists() or MODES_PATH.stat().st_size < 5:
        save_modes(DEFAULT_MODES)
    # Transcriber is initialized later in background thread


def init_transcriber_task():
    global transcriber
    try:
        # Prefer CUDA or DirectML if available and not explicitly set to CPU
        device = config.get("device", "auto")
        if device == "auto":
            if cuda_available:
                device = "cuda"
            elif dml_available:
                device = "dml"
            else:
                device = "cpu"
        
        current_model = config.get("model_size", "small")
        logger.info(f"Preparing transcriber: {current_model} on {device}...")
        app_state["status"] = "loading"
        app_state["status_message"] = f"Switching to {current_model}..."

        # If we already have a transcriber, its _load_model will now handle cleanup
        if transcriber is None:
            transcriber = Transcriber(
                model_size=current_model,
                device=device,
                compute_type=config.get("compute_type")
            )
        else:
            # Update parameters for existing instance
            transcriber.model_size = current_model
            transcriber.device = device
            transcriber.compute_type = config.get("compute_type")
        
        # This will trigger the cleanup of old model and load of new one
        transcriber._load_model()
        
        app_state["status"] = "ready"
        app_state["status_message"] = f"Whisper {current_model} Ready"
        app_state["error_message"] = None
        logger.info("Transcriber re-initialized successfully")
    except Exception as e:
        error_msg = f"Transcriber init error: {str(e)}"
        logger.error(error_msg)
        app_state["status"] = "error"
        app_state["error_message"] = error_msg


# --- Vosk Integration for Lightweight Real-Time Preview ---
vosk_model = None
vosk_ready = False
vosk_audio_queue = None

def init_vosk_task():
    global vosk_model, vosk_ready
    try:
        import vosk
        logger.info("Initializing Vosk model for real-time preview...")
        # Setting explicit logging off to avoid console noise
        vosk.SetLogLevel(-1)
        vosk_model = vosk.Model(lang="ja")
        vosk_ready = True
        logger.info("Vosk model ready.")
    except Exception as e:
        logger.warning(f"Failed to load Vosk model: {e}. Real-time preview will be unavailable.")
        vosk_ready = False

def vosk_worker_loop(q, model):
    import vosk
    import json
    try:
        rec = vosk.KaldiRecognizer(model, 16000)
        while True:
            item = q.get()
            if item is None:
                break
            
            # Convert NumPy float32 to int16 bytes
            pcm_bytes = (item * 32767).astype(np.int16).tobytes()
            if rec.AcceptWaveform(pcm_bytes):
                pass
            
            partial = json.loads(rec.PartialResult())
            txt = partial.get("partial", "")
            if txt:
                # For Japanese, strip spaces between segments for natural UI rendering
                if config.get("language") == "ja":
                    txt = txt.replace(" ", "")
                app_state["partial_transcript"] = txt
                # FORCED DIAGNOSTIC: Ensure text is visible somewhere if bubble fails
                app_state["status_message"] = txt
    except Exception as e:
        logger.error(f"Vosk worker crash: {e}")


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
    """Parse a hotkey string like 'Alt+Shift+S' or 'F1' into a set of pynput keys."""
    if not hotkey_str:
        return set()
    
    # Electron uses '+' as separator, pynput often uses '+' too. 
    # Ensure we handle various formats.
    parts = [p.strip().lower() for p in hotkey_str.replace('+', ' ').split()]
    keys = set()
    for p in parts:
        # 1. Check our defined map (ctrl, alt, shift, f1, f2...)
        if p in KEY_MAP:
            keys.add(KEY_MAP[p])
        # 2. Check if it's a single character (A, B, C...)
        elif len(p) == 1:
            try:
                # pynput expects uppercase for chars in some cases, 
                # but KeyCode.from_char handles lowercase fine for virtual keys
                keys.add(KeyCode.from_char(p))
            except Exception:
                pass
        # 3. Last resort fallback
        else:
            try:
                # Maybe it's a pynput key name we missed
                keys.add(getattr(Key, p))
            except:
                pass
    return keys

def on_press(key):
    try:
        global config
        if config.get("mode", "toggle") != "hold":
            return
        target_keys = parse_hotkey(config.get("hotkey", "Alt+Shift+S"))
        
        # Add the pressed key to the set of active keys
        active_keys.add(key)
        
        # Check if all target keys are currently pressed
        if target_keys and target_keys.issubset(active_keys):
            # Toggle logic
            if not app_state["is_recording"]:
                logger.info(f"Toggle-to-Talk: Start (Keys: {config.get('hotkey')})")
                trigger_start_sync()
            else:
                logger.info(f"Toggle-to-Talk: Stop (Keys: {config.get('hotkey')})")
                trigger_stop_sync()
            
            # Clear active keys to prevent rapid repeated toggles while holding down
            active_keys.clear()
    except Exception as e:
        logger.error(f"Error in on_press: {e}")

def on_release(key):
    try:
        global config
        if config.get("mode", "toggle") != "hold":
            return
        # Normalize key removal
        if key in active_keys:
            active_keys.remove(key)
    except Exception as e:
        logger.error(f"Error in on_release: {e}")



def trigger_start_sync():
    global target_hwnd
    if transcriber is None or app_state["is_recording"]: return
    
    try:
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

        # Set up Vosk live stream
        global vosk_audio_queue
        app_state["partial_transcript"] = ""
        if vosk_ready and vosk_model:
            vosk_audio_queue = queue.Queue()
            t = threading.Thread(target=vosk_worker_loop, args=(vosk_audio_queue, vosk_model), daemon=True)
            t.start()

        def audio_data_callback(data):
            if vosk_audio_queue is not None:
                vosk_audio_queue.put(data)

        if recorder:
            recorder.start_recording(on_audio_data=audio_data_callback)
        else:
            logger.warning("AudioRecorder unavailable; cannot start recording.")
        app_state["is_recording"] = True
        app_state["status"] = "recording"
        app_state["error_message"] = None
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        app_state["is_recording"] = False
        app_state["status"] = "error"
        app_state["error_message"] = f"Start recording failed: {str(e)}"


def trigger_stop_sync():
    try:
        if not app_state["is_recording"]: return
        app_state["is_recording"] = False
        
        # Terminate current Vosk session stream
        global vosk_audio_queue
        if vosk_audio_queue is not None:
            vosk_audio_queue.put(None)
            vosk_audio_queue = None

        app_state["status"] = "analyzing"
        threading.Thread(target=process_and_paste_task).start()
    except Exception as e:
        logger.error(f"Failed to stop recording or launch task: {e}")
        app_state["is_recording"] = False
        app_state["status"] = "ready"


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
        
        is_fallback = False
        if config.get("use_ollama", True):
            provider = config.get("ai_provider", "ollama")
            base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip('/')
            model = config.get("ollama_model", "qwen2.5-coder:14b")
            api_key = config.get("api_key", "")
            
            # Get current mode prompt
            active_mode_id = config.get("active_mode_id", "general")
            modes = load_modes()
            active_mode = next((m for m in modes if m["id"] == active_mode_id), None)
            
            if active_mode:
                system_prompt = active_mode.get("prompt", "校正してください。")
                prompt = f"{system_prompt}\n\n入力テキスト:\n{raw_text}"
            else:
                prompt = f"以下の文章を校正して、修正後の文章のみ出力してください:\n{raw_text}"
            
            refined_text = raw_text
            try:
                with httpx.Client() as client:
                    if provider == "ollama":
                        url = f"{base_url}/api/generate"
                        resp = client.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=60.0)
                        if resp.status_code == 200:
                            refined_text = resp.json().get("response", raw_text)
                    
                    elif provider == "openai":
                        url = f"{base_url}/v1/chat/completions" if "localhost" not in base_url else "https://api.openai.com/v1/chat/completions"
                        headers = {"Authorization": f"Bearer {api_key}"}
                        payload = {
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}]
                        }
                        resp = client.post(url, json=payload, headers=headers, timeout=60.0)
                        if resp.status_code == 200:
                            refined_text = resp.json()["choices"][0]["message"]["content"]

                    elif provider == "lmstudio":
                        lm_base = base_url if "v1" in base_url else f"{base_url}/v1"
                        # Auto-detect currently loaded model in LM Studio to avoid model name mismatch errors
                        active_model = model
                        try:
                            models_resp = client.get(f"{lm_base}/models", timeout=3.0)
                            if models_resp.status_code == 200:
                                loaded_models = [m["id"] for m in models_resp.json().get("data", [])]
                                if loaded_models and (not active_model or active_model not in loaded_models):
                                    active_model = loaded_models[0]
                        except Exception:
                            pass

                        url = f"{lm_base}/chat/completions"
                        headers = {"Authorization": "Bearer lm-studio"}
                        payload = {
                            "model": active_model,
                            "messages": [{"role": "user", "content": prompt}]
                        }
                        resp = client.post(url, json=payload, headers=headers, timeout=60.0)
                        if resp.status_code == 200:
                            refined_text = resp.json()["choices"][0]["message"]["content"]

                    elif provider == "gemini":
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                        payload = {"contents": [{"parts": [{"text": prompt}]}]}
                        resp = client.post(url, json=payload, timeout=60.0)
                        if resp.status_code == 200:
                            refined_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]

                    logger.info(f"Refined via {provider} ({active_mode_id})")
            except Exception as e:
                logger.error(f"AI Refinement failed: {e}")
                refined_text = raw_text
                is_fallback = True
        else:
            refined_text = raw_text
        
        # Final cleanup and Smart Insertion
        final_text = str(refined_text).strip()
        
        if final_text:
            logger.info(f"Final text for paste (len: {len(final_text)})")
            # Auto-Punctuation
            if config.get("auto_punctuation", True):
                punc_marks = (".", "!", "?", "。", "！", "？", ",", "、")
                if not final_text.endswith(punc_marks):
                    if config.get("language") == "ja":
                        # For Japanese, check if it looks like a complete sentence
                        if len(final_text) > 3:
                            final_text += "。"
                    else:
                        final_text += "."
            
            if is_fallback:
                final_text += " （フォールバック）"
            
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
            send_paste_command()

    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error(error_msg)
        app_state["status"] = "error"
        app_state["error_message"] = error_msg
    finally:
        app_state["is_recording"] = False
        if app_state["status"] != "error":
            app_state["status"] = "ready"
            app_state["status_message"] = None
        if os.path.exists(audio_path):
            os.remove(audio_path)

def refine_and_paste(raw_text):
    """Refine existing text with current config and paste it."""
    try:
        app_state["status"] = "analyzing"
        start_time = time.time()
        
        # Apply Vocabulary
        vocabulary = load_vocabulary()
        for item in vocabulary:
            if item.get("original") and item.get("replacement"):
                raw_text = raw_text.replace(item["original"], item["replacement"])
        
        is_fallback = False
        if config.get("use_ollama", True):
            provider = config.get("ai_provider", "ollama")
            base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip('/')
            model = config.get("ollama_model", "qwen2.5-coder:14b")
            api_key = config.get("api_key", "")
            active_mode_id = config.get("active_mode_id", "general")
            modes = load_modes()
            active_mode = next((m for m in modes if m["id"] == active_mode_id), None)
            
            system_prompt = active_mode.get("prompt", "校正してください。") if active_mode else "校正してください。"
            prompt = f"{system_prompt}\n\n入力テキスト:\n{raw_text}"
            
            refined_text = raw_text
            try:
                with httpx.Client() as client:
                    if provider == "ollama":
                        resp = client.post(f"{base_url}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=60.0)
                        if resp.status_code == 200: refined_text = resp.json().get("response", raw_text)
                    elif provider == "openai":
                        url = f"{base_url}/v1/chat/completions" if "localhost" not in base_url else "https://api.openai.com/v1/chat/completions"
                        resp = client.post(url, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, headers={"Authorization": f"Bearer {api_key}"}, timeout=60.0)
                        if resp.status_code == 200: refined_text = resp.json()["choices"][0]["message"]["content"]
                    elif provider == "lmstudio":
                        lm_base = base_url if "v1" in base_url else f"{base_url}/v1"
                        # Auto-detect currently loaded model in LM Studio to avoid model name mismatch errors
                        active_model = model
                        try:
                            models_resp = client.get(f"{lm_base}/models", timeout=3.0)
                            if models_resp.status_code == 200:
                                loaded_models = [m["id"] for m in models_resp.json().get("data", [])]
                                if loaded_models and (not active_model or active_model not in loaded_models):
                                    active_model = loaded_models[0]
                        except Exception:
                            pass

                        url = f"{lm_base}/chat/completions"
                        resp = client.post(url, json={"model": active_model, "messages": [{"role": "user", "content": prompt}]}, headers={"Authorization": "Bearer lm-studio"}, timeout=60.0)
                        if resp.status_code == 200: refined_text = resp.json()["choices"][0]["message"]["content"]
                    elif provider == "gemini":
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                        resp = client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60.0)
                        if resp.status_code == 200: refined_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error(f"Refinement error: {e}")
                is_fallback = True
        else:
            refined_text = raw_text

        final_text = refined_text.strip()
        if is_fallback:
            final_text += " （フォールバック）"
        # (Auto-Punctuation logic could be added here too)
        
        pyperclip.copy(final_text)
        send_paste_command()
        
        # Save updated version to history
        history = load_history()
        history_item = {
            "id": int(time.time() * 1000),
            "timestamp": datetime.now().isoformat(),
            "model": f"{config.get('ollama_model')} (Reprocessed)",
            "original": raw_text,
            "text": final_text,
            "chars": len(final_text),
            "duration": round(time.time() - start_time, 2)
        }
        history.insert(0, history_item)
        save_history(history[:100])

    except Exception as e:
        logger.error(f"Reprocess error: {e}")
    finally:
        app_state["status"] = "ready"

def send_paste_command():
    try:
        # If target_hwnd is not set, try to get current foreground window as fallback
        current_target = target_hwnd if target_hwnd else user32.GetForegroundWindow()
        
        if current_target:
            # Get the thread IDs
            foreground_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
            target_thread = user32.GetWindowThreadProcessId(current_target, None)
            
            # Try to attach thread input to bypass focus restrictions
            if foreground_thread != target_thread:
                try:
                    user32.AttachThreadInput(foreground_thread, target_thread, True)
                    user32.SetForegroundWindow(current_target)
                    user32.SetFocus(current_target)
                    user32.AttachThreadInput(foreground_thread, target_thread, False)
                except Exception as e:
                    logger.warning(f"AttachThreadInput/SetFocus failed: {e}")
            else:
                user32.SetForegroundWindow(current_target)
            
            time.sleep(0.3)
        
        # Send Paste command
        with keyboard_controller.pressed(Key.ctrl):
            keyboard_controller.tap('v')
        
        logger.info("Paste command sent successfully.")
    except Exception as e:
        logger.error(f"send_paste_command critical error: {e}")
    finally:
        # ABSOLUTELY ENSURE all modifiers are released no matter what
        for m_key in [Key.ctrl, Key.shift, Key.alt, Key.cmd]:
            try:
                keyboard_controller.release(m_key)
            except: pass
        logger.debug("All modifier keys released safely.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_globals()
    threading.Thread(target=init_transcriber_task, daemon=True).start()
    threading.Thread(target=init_vosk_task, daemon=True).start()
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
    if app_state.get("is_reloading"):
        status["status"] = "reloading"
    
    # Add engine readiness info
    status["engine_ready"] = engine_ready
    status["cuda_available"] = cuda_available
    status["dml_available"] = dml_available
    
    # Check AI Provider connectivity with 3-second caching to prevent port exhaustion
    provider_connected = False
    provider = config.get("ai_provider", "ollama")
    base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip('/')
    
    current_time = time.time()
    last_check = app_state.get("last_ai_check_time", 0.0)
    
    if current_time - last_check < 3.0:
        provider_connected = app_state.get("last_ai_check_result", False)
    else:
        app_state["last_ai_check_time"] = current_time
        try:
            async with httpx.AsyncClient() as client:
                if provider == "lmstudio":
                    resp = await client.get(f"{base_url}/models", timeout=0.5)
                    provider_connected = (resp.status_code == 200)
                elif provider in ["openai", "gemini"]:
                    provider_connected = True
                else:
                    resp = await client.get(f"{base_url}/api/tags", timeout=0.5)
                    provider_connected = (resp.status_code == 200)
        except:
            pass
        app_state["last_ai_check_result"] = provider_connected
    
    status["ollama_connected"] = provider_connected

    # Explicitly cast to float to avoid numpy JSON serialization error
    status["volume"] = float(recorder.current_volume) if recorder else 0.0
    return status


@app.get("/devices")
async def get_devices():
    if AudioRecorder:
        devices = AudioRecorder.get_input_devices()
        current_device_id = config.get("device_index")
        for d in devices:
            d["is_selected"] = (d["id"] == current_device_id)
        return devices
    else:
        logger.warning("AudioRecorder unavailable; cannot list devices.")
        return []


@app.get("/lmstudio/models")
async def get_lmstudio_models(base_url: str = None):
    if not base_url:
        base_url = config.get("ollama_base_url", "http://localhost:1234/v1")
    base_url = base_url.rstrip('/')
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}/models", timeout=3.0)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"data": []}
    except Exception as e:
        logger.error(f"Error fetching LM Studio models: {e}")
        return {"data": []}


@app.get("/config")
async def get_config():
    return load_config()

@app.post("/config")
async def save_config(new_config: dict):
    global config, recorder
    logger.info(f"Saving new config")
    try:
        old_config = config.copy()
        # Merge new_config into the existing config to prevent losing fields
        merged_config = old_config.copy()
        merged_config.update(new_config)
        save_config_file(merged_config)
        config = load_config()
        
        # 1. Update recorder ONLY if device_index actually changed
        if old_config.get("device_index") != config.get("device_index"):
            logger.info("Audio device changed. Updating recorder...")
            device_index = config.get("device_index")
            device_name = "System Default"
            if device_index is not None and device_index != -1:
                try:
                    devices = AudioRecorder.get_input_devices()
                    for d in devices:
                        if d.get("id") == device_index:
                            device_name = d.get("name")
                            break
                except Exception as e:
                    logger.error(f"Failed to get device name for index {device_index}: {e}")
            
            merged_config["device_name"] = device_name
            save_config_file(merged_config)
            config = load_config()
            recorder = AudioRecorder(device_index=config.get("device_index"))
        
        # 2. Reload transcriber ONLY if model or device settings actually changed
        needs_model_reload = (
            old_config.get("model_size") != config.get("model_size") or 
            old_config.get("device") != config.get("device") or
            old_config.get("compute_type") != config.get("compute_type")
        )
        
        if needs_model_reload:
            logger.info("Model settings changed. Re-initializing transcriber in background...")
            threading.Thread(target=init_transcriber_task).start()
        else:
            # If model didn't change, we stay ready (no need for Loading state)
            if app_state["status"] == "loading" and not needs_model_reload:
                app_state["status"] = "ready"
            
        logger.info("Config saved successfully (Fast update applied)")
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/reload")
async def config_reload():
    logger.info("Reloading config signal received from main process")
    app_state["is_reloading"] = True
    app_state["status_message"] = "Reloading Configuration..."
    try:
        global config, recorder
        config = load_config()
        # Update recorder if device changed
        recorder = AudioRecorder(device_index=config.get("device_index"))
        time.sleep(0.5) # Give a small buffer for sync
        return {"status": "ok"}
    finally:
        app_state["is_reloading"] = False

@app.post("/start")
async def api_start():
    try:
        trigger_start_sync()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"API /start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
async def api_stop():
    trigger_stop_sync()
    return {"status": "ok"}

@app.get("/history")
async def get_history():
    return load_history()

@app.post("/history/delete")
async def delete_history(payload: dict):
    history_id = payload.get("id")
    if history_id is None:
        raise HTTPException(400, "History ID required")
    
    history = load_history()
    new_history = [h for h in history if h.get("id") != history_id]
    
    if len(new_history) == len(history):
        raise HTTPException(404, "History item not found")
        
    save_history(new_history)
    return {"status": "ok"}

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
    elif action == "update":
        idx = payload.get("index")
        item = payload.get("item")
        if idx is not None and 0 <= idx < len(vocab) and item:
            vocab[idx] = item
    save_vocabulary(vocab)
    return {"status": "ok", "vocabulary": vocab}

from fastapi import Request

@app.post("/vocabulary/import")
async def import_vocabulary(request: Request):
    try:
        new_vocab = await request.json()
        if not isinstance(new_vocab, list):
            # If the JSON is an object with a 'rules' or 'vocabulary' key, extract it
            if isinstance(new_vocab, dict):
                new_vocab = new_vocab.get("rules") or new_vocab.get("vocabulary") or []
            else:
                new_vocab = []

        existing_vocab = load_vocabulary()
        merged = {str(item["original"]): item["replacement"] for item in existing_vocab if isinstance(item, dict) and "original" in item}
        
        added_count = 0
        for item in new_vocab:
            if not isinstance(item, dict): continue
            orig = item.get("original") or item.get("orig") # Support common aliases
            repl = item.get("replacement") or item.get("repl")
            if orig and repl:
                orig_str = str(orig)
                if orig_str not in merged:
                    added_count += 1
                merged[orig_str] = repl
        
        final_vocab = [{"original": k, "replacement": v} for k, v in merged.items()]
        save_vocabulary(final_vocab)
        logger.info(f"Vocabulary import successful: {added_count} rules added. Total: {len(final_vocab)}")
        return {"status": "ok", "added": added_count, "total": len(final_vocab)}
    except Exception as e:
        logger.error(f"Error importing vocabulary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            deleted_mode = modes.pop(idx)
            # Fallback if active mode was deleted
            global config
            if config.get("active_mode_id") == deleted_mode.get("id"):
                config["active_mode_id"] = "general"
                save_config_file(config)
    elif action == "update":
        idx = payload.get("index")
        item = payload.get("item")
        if idx is not None and 0 <= idx < len(modes):
            modes[idx] = item
    save_modes(modes)
    return {"status": "ok", "modes": modes}

@app.get("/ollama/models")
async def get_ollama_models():
    base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip('/')
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"models": []}
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {e}")
        return {"models": []}

@app.post("/ollama/pull")
async def pull_ollama_model(payload: dict):
    model = payload.get("model")
    if not model:
        raise HTTPException(400, "Model name required")
    
    def pull_task():
        base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip('/')
        try:
            logger.info(f"Starting to pull model: {model} from {base_url}")
            with httpx.Client() as client:
                client.post(f"{base_url}/api/pull", json={"name": model, "stream": False}, timeout=None)
            logger.info(f"Finished pulling model: {model}")
        except Exception as e:
            logger.error(f"Error pulling model {model}: {e}")

    threading.Thread(target=pull_task).start()
    return {"status": "started", "model": model}

@app.post("/paste")
async def api_paste(payload: dict):
    text = payload.get("text")
    if not text:
        raise HTTPException(400, "Text required")
    
    pyperclip.copy(text)
    
    # We need to wait a bit so the settings window can hide and focus returns to the previous app
    def delayed_paste():
        time.sleep(0.8) # Wait for focus transition
        send_paste_command()
    
    threading.Thread(target=delayed_paste).start()
    return {"status": "ok"}

@app.post("/reprocess_last")
async def api_reprocess_last():
    history = load_history()
    if not history:
        raise HTTPException(404, "No history to reprocess")
    
    last_original = history[0].get("original")
    if not last_original:
        raise HTTPException(400, "Last history item has no original text")
    
    threading.Thread(target=refine_and_paste, args=(last_original,)).start()
    return {"status": "started"}

@app.get("/engine/check")
async def api_engine_check():
    return {
        "info": check_full_environment(),
        "setup_status": app_state["setup_status"],
        "setup_progress": app_state["setup_progress"]
    }

@app.post("/engine/setup")
async def api_engine_setup(payload: dict):
    type = payload.get("type", "base") # base or gpu
    
    if app_state["setup_status"] != "idle" and app_state["setup_status"] != "finished":
        return {"status": "error", "message": "Setup already in progress"}

    def setup_task():
        try:
            app_state["setup_status"] = "installing"
            app_state["setup_progress"] = 10
            logger.info(f"Starting Engine Setup: {type}")
            
            import subprocess
            import sys
            
            # Determine which requirements to use
            if type == "base":
                req_file = "requirements-base.txt"
            elif type == "dml":
                req_file = "requirements-dml.txt"
            else:
                req_file = "requirements-gpu.txt"
            req_path = os.path.join(os.path.dirname(__file__), req_file)
            
            app_state["setup_progress"] = 30
            # Run pip install
            cmd = [sys.executable, "-m", "pip", "install", "-r", req_path]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            for line in process.stdout:
                logger.info(f"[PIP] {line.strip()}")
                # Basic progress simulation
                if app_state["setup_progress"] < 90:
                    app_state["setup_progress"] += 1
            
            process.wait()
            
            if process.returncode == 0:
                app_state["setup_status"] = "finished"
                app_state["setup_progress"] = 100
                logger.info("Engine Setup Finished Successfully")
                # Trigger a reload after a short delay
                time.sleep(2)
                os._exit(0) # Restart server to pick up new libraries
            else:
                app_state["setup_status"] = "error"
                logger.error(f"Engine Setup Failed with code {process.returncode}")
        except Exception as e:
            app_state["setup_status"] = "error"
            logger.error(f"Setup error: {e}")

    threading.Thread(target=setup_task).start()
    return {"status": "started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8240)
