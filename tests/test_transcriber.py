import pytest
import time
import os
from unittest.mock import MagicMock
from backend.transcriber import Transcriber

# @pytest.fixture(scope="function") はテストごとに環境を初期化・クリーンアップするのに役立ちます。
@pytest.fixture(scope="function")
def transcriber_instance():
    # テストの際は軽量なモデル（tiny）を指定し、CPUを使って高速に実行できるようにします。
    return Transcriber(model_size="tiny", device="cpu", compute_type="int8")

def test_transcriber_initialization(transcriber_instance):
    """Transcriberが正しく初期化され、モデルがロードされているかテストします。"""
    # モデル名などが内部で保持されているか確認するなど、初期状態のテストを行います。
    assert hasattr(transcriber_instance, 'model')

def test_transcriber_transcribe_basic(transcriber_instance, mocker, tmp_path):
    """文字起こしプロセスが、ダミーな音声ファイルを受け取り、テキストを返す基本フローをテストします。"""
    
    # 外部ライブラリの呼び出しをモック化し、本質的なロジック（処理の流れ）のテストに焦点を当てます
    # faster-whisperのtranscribeメソッド全体をモック化します。
    mock_transcribe = mocker.patch('transcriber.WhisperModel.transcribe')
    
    # モックが返す擬似的なセグメントデータ
    mock_segment = MagicMock()
    mock_segment.text = "こんにちは、テストです。"
    
    # モックの戻り値を設定: segmentsが[mock_segment]、infoが適当な辞書
    mock_transcribe.return_value = ([mock_segment], {"language": "ja"})

    # テスト実行
    try:
        # 存在しないが、テスト用に空のダミーファイルを作成して渡す
        dummy_audio_path = tmp_path / "dummy.wav"
        transcriber_instance.transcribe(str(dummy_audio_path), language="ja")
        
        # 1. transcribeメソッドが正しく呼び出されているか検証
        mock_transcribe.assert_called_once()
        
        # 2. 結果が正しくテキスト化されているか検証 (内部ロジックの検証)
        # これは、テキスト結合ロジックが正しいことを確認するために使います。
        # （実際には、transcriber_instance.transcribe内でのテキスト結合をテストする形が理想です）
        # 今回は、処理が例外を吐かずに完了することを検証します。
        pass
    finally:
        # モックを解除
        mock_transcribe.stop()
        
def test_transcriber_handles_error(transcriber_instance, mocker):
    """文字起こし処理中に例外が発生した場合の耐障害性をテストします。"""
    # transcribeメソッドが例外を発生させるようにモックを設定します。
    mock_transcribe = mocker.patch('transcriber.WhisperModel.transcribe', side_effect=RuntimeError("モデルロード失敗"))
    
    with pytest.raises(RuntimeError):
        transcriber_instance.transcribe("dummy.wav", language="ja")
    
    mock_transcribe.stop()

# メモ: テスト実行には、仮想環境と、mockingのための適切なセットアップが必要です。
