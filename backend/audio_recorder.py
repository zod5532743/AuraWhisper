import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioRecorder:
    def __init__(self, sample_rate=16000, device_index=None):
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.recording = []
        self.is_recording = False
        self.current_volume = 0.0


    @staticmethod
    def get_input_devices():
        devices = sd.query_devices()
        input_devices = []
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                input_devices.append({
                    "id": i,
                    "name": d['name'],
                    "hostapi": d['hostapi']
                })
        return input_devices

    def start_recording(self):
        logger.info(f"Starting recording on device {self.device_index}...")
        self.recording = []
        self.is_recording = True
        
        # Callback to collect audio data
        def callback(indata, frames, time, status):
            if status:
                logger.warning(status)
            if self.is_recording:
                self.recording.append(indata.copy())
                # Calculate RMS for volume visualization
                rms = np.sqrt(np.mean(indata**2))
                # Scale RMS to 0.0 - 1.0 roughly
                v = min(1.0, rms * 50.0)
                self.current_volume = v
                if v > 0.05:
                    logger.info(f"🎤 Mic Level: {v:.4f}")


        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate, 
                channels=1, 
                callback=callback,
                device=self.device_index
            )
            self.stream.start()
        except Exception as e:
            logger.error(f"Failed to start recording stream: {e}")
            self.is_recording = False
            raise e

    def stop_recording(self):
        logger.info("Stopping recording...")
        self.is_recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        if not self.recording:
            return None

        audio_data = np.concatenate(self.recording, axis=0)
        
        # Save to a temporary wav file
        fd, path = tempfile.mkstemp(suffix=".wav")
        try:
            wav.write(path, self.sample_rate, audio_data)
        finally:
            os.close(fd)
            
        return path

if __name__ == "__main__":
    # Test recording for 3 seconds
    import time
    recorder = AudioRecorder()
    recorder.start_recording()
    time.sleep(3)
    path = recorder.stop_recording()
    print(f"Recorded to {path}")
