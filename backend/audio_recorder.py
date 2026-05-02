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
        # In UI, -1 represents "Auto" (default device), but sounddevice expects None
        self.device_index = None if device_index == -1 else device_index
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
        # Double check device index normalization
        actual_device = None if self.device_index == -1 else self.device_index
        logger.info(f"Starting recording on device: {actual_device if actual_device is not None else 'Default'}")
        
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
                # Lower log level for volume to avoid flooding logs
                # if v > 0.05:
                #     logger.debug(f"🎤 Mic Level: {v:.4f}")


        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate, 
                channels=1, 
                callback=callback,
                device=actual_device
            )
            self.stream.start()
        except Exception as e:
            logger.error(f"Failed to start recording stream on device {actual_device}: {e}. Falling back to default device...")
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate, 
                    channels=1, 
                    callback=callback,
                    device=None
                )
                self.stream.start()
            except Exception as e2:
                logger.error(f"Critical error on default device fallback: {e2}")
                self.is_recording = False
                raise e2


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
