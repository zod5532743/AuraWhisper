import os
import time
from faster_whisper import WhisperModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self, model_size="large-v3", device="cuda", compute_type=None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def _load_model(self):
        # If we already have a model but it's not the right size/device, clear it
        # Note: server.py handles the logic of when to call this.
        
        import gc
        if self.model is not None:
            logger.info("Clearing existing Whisper model to free memory...")
            self.model = None
            gc.collect()
            if self.device == "cuda":
                try:
                    import ctranslate2
                    ctranslate2.unload_model(self.model_size) # Best effort
                except: pass
            time.sleep(1) # Give OS a moment to reclaim memory

        if self.compute_type is None:
            # CPU 'int8' can be unstable on some Windows setups, using 'float32' for safety
            self.compute_type = "float16" if self.device == "cuda" else "float32"
        
        model_to_load = self.model_size
        if model_to_load == "large-v3-turbo":
            model_to_load = "Systran/faster-whisper-large-v3" # Using Systran version as safer fallback

        logger.info(f"Loading Whisper model: {model_to_load} on {self.device} ({self.compute_type})...")
        try:
            # Explicitly set download_root to use the decoupled models directory
            download_root = os.environ.get("HF_HOME")
            self.model = WhisperModel(
                model_to_load, 
                device=self.device, 
                compute_type=self.compute_type,
                download_root=download_root
            )
        except Exception as e:
            logger.error(f"Failed to load model {model_to_load} from {download_root}: {e}. Falling back to CPU...")
            try:
                self.model = WhisperModel(model_to_load, device="cpu", compute_type="float32", download_root=download_root)
            except Exception as e2:
                logger.error(f"Critical fallback failure: {e2}")
                self.model = None
        
        logger.info("Model loaded successfully.")

    def transcribe(self, audio_path, language="ja"):
        if self.model is None:
            self._load_model()
        logger.info(f"Transcribing {audio_path}...")
        start_time = time.time()
        
        segments, info = self.model.transcribe(audio_path, beam_size=5, language=language)
        
        # Convert to list to avoid generator-related crashes/hangs
        segments = list(segments)
        
        text = "".join([segment.text for segment in segments])
            
        duration = time.time() - start_time
        logger.info(f"Transcription finished in {duration:.2f}s.")
        return text.strip()

if __name__ == "__main__":
    # Test script
    transcriber = Transcriber(model_size="tiny", device="cpu", compute_type="int8")
    # result = transcriber.transcribe("test.wav")
    # print(result)
