import os
import sys
import time

# Add NVIDIA DLL directories to path on Windows
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if os.path.exists(backend_dir):
    sys.path.insert(0, backend_dir)

venv_site_packages = os.path.join(backend_dir, "venv", "Lib", "site-packages")
nvidia_base = os.path.join(venv_site_packages, "nvidia")
if os.name == 'nt' and os.path.exists(nvidia_base):
    for root, dirs, files in os.walk(nvidia_base):
        if 'bin' in dirs:
            bin_path = os.path.normpath(os.path.join(root, 'bin'))
            print(f"Adding DLL directory: {bin_path}")
            os.add_dll_directory(bin_path)
            os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]

try:
    from transcriber import Transcriber
    print("Transcriber imported successfully.")
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Check models directory
models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))
os.environ["HF_HOME"] = models_dir
os.environ["XDG_CACHE_HOME"] = models_dir
os.environ["HF_HUB_CACHE"] = models_dir

print(f"Models Dir: {models_dir}")

# Load Transcriber
try:
    # Use auto or cpu device depending on availability
    # But let's check CUDA directly to see if it works or fails
    device = "cpu"
    try:
        import ctranslate2
        cuda_avail = ctranslate2.get_cuda_device_count() > 0
        if cuda_avail:
            device = "cuda"
            print("CUDA detected in test.")
    except Exception as e:
        print(f"Error checking CUDA: {e}")

    print(f"Initializing transcriber with model 'small' on {device}...")
    transcriber = Transcriber(model_size="small", device=device)
    transcriber._load_model()
    print("Transcriber initialized successfully.")

    # Create dummy silent audio for testing
    import numpy as np
    import scipy.io.wavfile as wav
    import tempfile

    sample_rate = 16000
    # 3 seconds of silent audio
    audio_data = np.zeros(sample_rate * 3, dtype=np.float32)
    
    fd, audio_path = tempfile.mkstemp(suffix=".wav")
    try:
        wav.write(audio_path, sample_rate, audio_data)
        print(f"Created temporary dummy audio file at {audio_path}")

        print("Testing transcription...")
        start_time = time.time()
        text = transcriber.transcribe(audio_path)
        print(f"Transcription result: [{text}] (took {time.time() - start_time:.2f}s)")
    finally:
        os.close(fd)
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print("Cleaned up temporary audio.")

except Exception as e:
    print(f"An error occurred during test: {e}")
