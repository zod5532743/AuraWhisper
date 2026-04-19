import sounddevice as sd
import sys

def debug_audio_devices():
    print("=== オーディオデバイス デバッグツール ===\n")

    try:
        print("--- 入力デバイス (Input Devices) ---")
        print(sd.query_devices())
        print("\n")

        print("--- 出力デバイス (Output Devices) ---")
        print(sd.query_devices())
        print("\n")

        print("--- 現在のデフォルト設定 ---")
        print(f"Default Input Device ID: {sd.default.device[0]}")
        print(f"Default Output Device ID: {sd.default.device[1]}")
        
        # デフォルト入力デバイスの名前を確認
        default_input_id = sd.default.device[0]
        if default_input_id != -1:
            devices = sd.query_devices()
            print(f"Default Input Device Name: {devices[default_input_id]['name']}")
        else:
            print("Default Input Device is NOT set (-1).")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        print("sounddevice ライブラリがインストールされていない可能性があります。")
        print("pip install sounddevice を実行してください。")

if __name__  == "__main__":
    debug_audio_devices()
