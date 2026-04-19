import os
import time
from faster_whisper import WhisperModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self, model_size="large-v3", device="cuda", compute_type="float16"):
        logger.info(f"Loading Whisper model: {model_size} on {device}...")
        # device="cuda" if available, else "cpu"
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info("Model loaded successfully.")

    def transcribe(self, audio_path, language="ja"):
        logger.info(f"Transcribing {audio_path}...")
        start_time = time.time()
        
        segments, info = self.model.transcribe(audio_path, beam_size=5, language=language)
        
        text = ""
        for segment in segments:
            text += segment.text
            
        duration = time.time() - start_time
        logger.info(f"Transcription finished in {duration:.2f}s.")
        return text.strip()

if __name__ == "__main__":
    # Test script
    transcriber = Transcriber(model_size="tiny", device="cpu", compute_type="int8")
    # result = transcriber.transcribe("test.wav")
    # print(result)
