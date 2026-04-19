import os
import time
from faster_whisper import WhisperModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self, model_size="large-v3", device="cuda", compute_type=None):
        if compute_type is None:
            # CPU 'int8' can be unstable on some Windows setups, using 'float32' for safety
            compute_type = "float16" if device == "cuda" else "float32"
        logger.info(f"Loading Whisper model: {model_size} on {device} ({compute_type})...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)


        logger.info("Model loaded successfully.")

    def transcribe(self, audio_path, language="ja"):
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
