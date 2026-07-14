import os
import time
import gc
import logging
import numpy as np

logger = logging.getLogger(__name__)


class DmlTranscriber:
    """
    DirectML-accelerated transcriber for AMD/Intel GPUs on Windows.
    
    2段階のバックエンド選択:
      1. optimum[onnxruntime] + DirectML (ONNX Runtime DmlExecutionProvider)
      2. CPU (transformers + PyTorch, GPU非依存)
    
    faster-whisper(CTranslate2)はDirectMLをサポートしないため、
    AMD GPUでは本クラスを使用して文字起こしを高速化します。
    """

    def __init__(self, model_size="small", device="dml", compute_type=None):
        self.model_size = model_size
        self.device = device          # "dml"
        self.compute_type = compute_type or "float32"
        self.model = None
        self.processor = None
        self._device_type = "cpu"     # 実際に使用中のバックエンド (dml / cpu)
        self._provider = None         # 使用中のプロバイダ名

    def _get_model_id(self):
        """model_size から HuggingFace モデルID を解決."""
        size = self.model_size
        mapping = {
            "large-v3-turbo": "openai/whisper-large-v3",
            "large":          "openai/whisper-large-v3",
            "medium":         "openai/whisper-medium",
            "small":          "openai/whisper-small",
            "base":           "openai/whisper-base",
            "tiny":           "openai/whisper-tiny",
        }
        return mapping.get(size, "openai/whisper-small")

    def _load_model(self):
        """モデルをロード。DirectML -> CPU の順で試行."""
        if self.model is not None:
            logger.info("既存のDMLモデルをクリア中...")
            self.model = None
            self.processor = None
            gc.collect()
            time.sleep(1)

        # 戦略1: optimum + ONNX Runtime DirectML
        if self._try_load_onnx_dml():
            return

        # 戦略2: CPU (トランスフォーマー)
        logger.warning("DirectMLバックエンドのロードに失敗しました。CPUでフォールバックします。")
        self._load_cpu_model()

    def _try_load_onnx_dml(self):
        """optimum[onnxruntime] + DirectML でモデルをロード."""
        try:
            from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
            from transformers import WhisperProcessor
            import onnxruntime as ort

            providers = ort.get_available_providers()
            logger.info(f"ONNX Runtime 利用可能プロバイダ: {providers}")

            if "DmlExecutionProvider" not in providers:
                logger.warning("DirectML execution provider が ONNX Runtime で利用できません。")
                return False

            model_id = self._get_model_id()
            logger.info(f"ONNX Whisper モデルをロード中: {model_id} (DirectML)")

            self.processor = WhisperProcessor.from_pretrained(model_id)

            # ONNX エクスポート + DirectML プロバイダでロード
            self.model = ORTModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                export=True,
                provider="DmlExecutionProvider",
                use_cache=True,
                use_merged=True,
            )

            self._device_type = "dml"
            self._provider = "DmlExecutionProvider"
            logger.info("ONNX DirectML モデルのロードが完了しました。")

            # ウォームアップ
            self._warmup()
            return True

        except ImportError as e:
            logger.warning(f"optimum/onnxruntime のインポートに失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"ONNX DirectML ロード失敗: {e}")
            return False

    def _load_cpu_model(self):
        """CPU フォールバック: transformers + PyTorch."""
        try:
            from transformers import WhisperProcessor, WhisperForConditionalGeneration
            import torch

            model_id = self._get_model_id()
            logger.info(f"Whisper モデルを CPU でロード中: {model_id}")

            self.processor = WhisperProcessor.from_pretrained(model_id)
            self.model = WhisperForConditionalGeneration.from_pretrained(model_id)
            self.model = self.model.to("cpu")
            self._device_type = "cpu"
            self._provider = "cpu"

            self._warmup()
            logger.info("CPU モデルのロードが完了しました。")

        except Exception as e:
            logger.error(f"CPU モデルロード失敗: {e}")
            raise

    def _warmup(self):
        """初回実行のレイテンシを削減するウォームアップ."""
        try:
            logger.info("DML モデルをウォームアップ中...")
            dummy_audio = np.zeros(16000, dtype=np.float32)
            self.transcribe_internal(dummy_audio, language="ja")
            logger.info("ウォームアップ完了。")
        except Exception as e:
            logger.warning(f"ウォームアップに失敗しました: {e}")

    def transcribe_internal(self, audio, language="ja"):
        """音声データ (numpy array, 16kHz) をテキスト化 (内部メソッド)."""
        inputs = self.processor(
            audio,
            sampling_rate=16000,
            return_tensors="np",       # ONNX Runtime は numpy 入力
            language=language,
        )

        if self._device_type == "dml":
            # optimum ONNX モデル: numpy をそのまま渡す
            predicted_ids = self.model.generate(
                **inputs,
                language=language,
                task="transcribe",
                max_length=448,
                num_beams=1,
            )
        else:
            # CPU transformers: numpy を torch tensor に変換
            import torch
            input_features = torch.from_numpy(inputs["input_features"]).float()
            with torch.no_grad():
                predicted_ids = self.model.generate(
                    input_features,
                    language=language,
                    task="transcribe",
                    max_length=448,
                    num_beams=1,
                )

        text = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        return text.strip()

    def transcribe(self, audio_path, language="ja"):
        """音声ファイルを文字起こし (外部向け I/F)."""
        if self.model is None or self.processor is None:
            self._load_model()

        logger.info(f"文字起こし中: {audio_path} (device: {self._device_type})")
        start_time = time.time()

        # 音声ファイルを読み込み、16kHz にリサンプリング
        try:
            import librosa
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        except Exception as e:
            logger.error(f"音声ファイル読み込み失敗: {e}")
            raise

        text = self.transcribe_internal(audio, language=language)

        duration = time.time() - start_time
        logger.info(f"文字起こし完了: {duration:.2f}s (device: {self._device_type})")
        return text

    def unload(self):
        """モデルをアンロードしてメモリを解放."""
        self.model = None
        self.processor = None
        gc.collect()
        logger.info("DML モデルをアンロードしました。")
