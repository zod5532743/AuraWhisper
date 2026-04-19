import pytest
import tempfile
import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav

# 関連モジュールのインポート
from backend.audio_recorder import AudioRecorder

# @pytest.fixture(scope="function") はテストごとに環境を初期化・クリーンアップするのに役立ちます。
@pytest.fixture(scope="function")
def recorder_instance():
    # シミュレートのためにデバイスインデックス指定などを省略します
    return AudioRecorder()

def test_audio_recorder_initialization(recorder_instance):
    """Recorderインスタンスが正しく初期化されるかテストします。"""
    assert isinstance(recorder_instance, AudioRecorder)

def test_audio_recorder_start_stop(recorder_instance, mocker):
    """録音開始と停止の基本的なフローをテストします。"""
    # 実際のデバイスアクセスは複雑なので、モックを使って内部ステートの変更を検証します。
    # sd.InputStreamの起動をモック化し、状態管理のテストに焦点を当てます。
    with mocker.patch("sounddevice.InputStream"):
        recorder_instance.start_recording()
        assert recorder_instance.is_recording == True
        
        recorder_instance.stop_recording()
        # 停止後はis_recordingがFalseに戻るべき
        assert recorder_instance.is_recording == False

import pytest
import numpy as np
import scipy.io.wavfile as wav
import os
from backend.audio_recorder import AudioRecorder

@pytest.fixture(scope="function")
def recorder_instance():
    return AudioRecorder()

def test_audio_recorder_initialization(recorder_instance):
    """Recorderインスタンスが正しく初期化されるかテストします。"""
    assert isinstance(recorder_instance, AudioRecorder)
    assert recorder_instance.is_recording is False

def test_audio_recorder_start_stop(recorder_instance, mocker):
    """録音開始と停止の基本的なフローをテストします。"""
    # sd.InputStreamの起動をモック化し、状態管理のテストに焦点を当てます。
    with mocker.patch("sounddevice.InputStream"):
        recorder_instance.start_recording()
        assert recorder_instance.is_recording is True
        
        recorder_instance.stop_recording()
        assert recorder_instance.is_recording is False

def test_audio_recorder_save_file_path(recorder_instance):
    """録音データがtempファイルに正しく保存されるかテストします。"""
    # ダミーの録音データを注入
    recorder_instance.is_recording = True
    dummy_data = np.random.uniform(-1, 1, 16000).reshape(-1, 1).astype(np.float32)
    recorder_instance.recording = [dummy_data]
    
    # 録音停止とファイル保存の実行
    path = recorder_instance.stop_recording()
    
    # 検証
    assert path is not None
    assert path.endswith(".wav")
    assert os.path.exists(path)
    
    # 保存されたwavファイルを読み込んで中身を検証
    samplerate, data = wav.read(path)
    assert samplerate == recorder_instance.sample_rate
    assert data.squeeze().shape == dummy_data.squeeze().shape
    
    # 後片付け
    if os.path.exists(path):
        os.remove(path)
