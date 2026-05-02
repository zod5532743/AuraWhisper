import sys
import os
# Add the current directory to sys.path to import audio_recorder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_recorder import AudioRecorder
import time
import logging

logging.basicConfig(level=logging.INFO)

def test_device_normalization():
    print("Testing AudioRecorder with device_index=-1 (Auto)...")
    try:
        # This should now normalize -1 to None
        recorder = AudioRecorder(device_index=-1)
        print(f"Recorder initialized. Internal device_index: {recorder.device_index}")
        
        if recorder.device_index is not None:
            print("FAILED: device_index should be None")
            return False
            
        print("Starting recording for 1 second...")
        recorder.start_recording()
        time.sleep(1)
        path = recorder.stop_recording()
        
        if path and os.path.exists(path):
            print(f"SUCCESS: Recorded to {path}")
            os.remove(path)
            return True
        else:
            print("FAILED: No audio file created")
            return False
            
    except Exception as e:
        print(f"FAILED: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_device_normalization()
    sys.exit(0 if success else 1)
