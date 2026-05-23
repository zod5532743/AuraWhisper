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
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, d in enumerate(devices):
                try:
                    if d.get('max_input_channels', 0) > 0:
                        name = d.get('name', f"Device {i}")
                        if isinstance(name, bytes):
                            name = name.decode('utf-8', errors='ignore')
                        
                        input_devices.append({
                            "id": i,
                            "name": name,
                            "hostapi": d.get('hostapi', 0)
                        })
                except Exception as e:
                    logger.warning(f"Error parsing device {i}: {e}")
            return input_devices
        except Exception as e:
            logger.error(f"Failed to query devices from sounddevice: {e}", exc_info=True)
            return []

    def start_recording(self, on_audio_data=None):
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
                # Allocate a brand-new independent memory block to prevent PortAudio ring-buffer memory overwriting
                data_copy = np.array(indata, dtype=np.float32, order='C')
                self.recording.append(data_copy)
                
                # Fire real-time stream callback if provided
                if on_audio_data:
                    try:
                        on_audio_data(data_copy)
                    except Exception as e:
                        pass # Suppress to keep audio loop healthy
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
                device=actual_device,
                blocksize=2048
            )
            self.stream.start()
        except Exception as e:
            logger.error(f"Failed to start recording stream on device {actual_device}: {e}. Falling back to default device...")
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate, 
                    channels=1, 
                    callback=callback,
                    device=None,
                    blocksize=2048
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
        
        # Trim first and last 0.3 seconds to remove hotkey click noise and physical button releases
        trim_samples = int(self.sample_rate * 0.3)
        if len(audio_data) > trim_samples * 2:
            audio_data = audio_data[trim_samples:-trim_samples]
            logger.info(f"Trimmed hotkey click noise (removed {trim_samples} samples from start/end).")
        
        # Automatic volume normalization to prevent Whisper hallucinations from low-input mic levels
        try:
            max_amp = np.abs(audio_data).max()
            if max_amp > 0.0001:
                # Normalize to max amplitude 0.9
                audio_data = audio_data * (0.9 / max_amp)
                logger.info(f"Audio normalized to prevent Whisper hallucination. Original max amp: {max_amp:.5f} -> 0.90000")
            else:
                logger.warning(f"Audio is virtually silent (max amplitude: {max_amp:.5f}). Normalization skipped.")
        except Exception as e:
            logger.error(f"Failed to normalize audio: {e}")
            
        # Convert float32 [-1.0, 1.0] to standard 16-bit PCM (int16) to ensure 100% compatibility with all decoders
        try:
            audio_data = (audio_data * 32767.0).astype(np.int16)
            logger.info("Audio converted to standard 16-bit PCM (int16).")
        except Exception as e:
            logger.error(f"Failed to convert audio to int16: {e}")
        
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
