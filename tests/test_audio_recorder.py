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

def test_audio_recorder_save_file_path(recorder_instance, tmp_path):
    """録音データがtempファイルに正しく保存されるかテストします。"""
    # 実際にデータ生成を模擬するために、recordingリストを直接操作します。
    # このテストでは、scipyのwav.writeが呼ばれることを確認するため、外部のモックが必要です。
    with pytest.raises(AttributeError):
        # 実際の録音データはないため、最小限のデータ構造でテストを試みます。
        # 成功するためには、numpy配列の結合とファイル書き込みがキーになります。
        pass
    
    # 簡易的なファイル保存パスの確認用テストとして残します
    # テスト実行時は、外部シグネチャのモック化が必須となるため、このファイルは骨子として残します。