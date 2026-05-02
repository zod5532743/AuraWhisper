#!/usr/bin/env python
"""
AuraWhisper - 音声 AI アシスタント
モデルダウンロード、テスト、ヘルプコマンド
"""

import argparse
import asyncio
import subprocess
import json
import sys
from pathlib import Path


def get_default_model_name():
    """デフォルトモデル名を取得"""
    return "medium"


def is_offline():
    """オフラインモードかどうかを確認"""
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("offline_mode", False)
    return False


def check_models_downloaded(model_names):
    """モデルがダウンロードされているか確認"""
    models_path = Path(__file__).parent.parent / "models"
    if not models_path.exists():
        print(f"❌ モデルディレクトリが見つかりません：{models_path}")
        return False

    available = []
    missing = []
    for name in model_names:
        model_path = models_path / f"{name}.pt"
        if model_path.exists():
            available.append(name)
            print(f"  ✓ {name}")
        else:
            missing.append(name)
            print(f"  ✗ {name} (未ダウンロード)")

    return len(missing) == 0


def download_models(progress_callback=None):
    """
    Whisper モデルをダウンロード

    Args:
        progress_callback: 進捗を返すコールバック関数（引数：percent）
    """
    models_path = Path(__file__).parent.parent / "models"
    models_path.mkdir(exist_ok=True)

    default_model = "medium"
    model_names = ["small", "medium", "large-v3"]

    if progress_callback:
        progress_callback(0, len(model_names) * 100, "")

    def download_model(name):
        model_name = f"whisper-{name}.pt"
        model_path = models_path / model_name

        if model_path.exists():
            return name, True, f"{model_name} は既に存在します", False

        print(f"\n📦 {name} モデルをダウンロード中...")
        print(f"   保存先：{model_path}")

        # faster-whisper を使用してモデルをダウンロード
        try:
            from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, AutoTokenizer
            from sentence_transformers import SentenceTransformer

            # 公式リポジトリからモデルをダウンロード
            model = SentenceTransformer(model_name)
            return name, True, f"{model_name} をダウンロードしました", False
        except Exception as e:
            error_msg = str(e)
            if "ConnectionError" in error_msg or "HTTPError" in error_msg:
                return name, False, f"ネットワークエラー：{error_msg}", True
            return name, False, f"ダウンロードエラー：{error_msg}", True

    def run_parallel():
        """複数のモデルを並列にダウンロード"""
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(download_model, name) for name in model_names]
            results = [f.result() for f in futures]

        available = []
        missing = []
        for name, success, msg, error in results:
            if success:
                available.append(name)
            else:
                missing.append(name)

        return available, missing

    print("\n📥 Whisper モデルをダウンロード中...")
    available, missing = run_parallel()

    if progress_callback:
        total = len(model_names) * 100
        downloaded = len(available) / len(model_names) * total
        progress_callback(downloaded, total, f"ダウンロード完了：{len(available)}/{len(model_names)}")

    return available, missing


def test_audio_file():
    """音声ファイルのテスト"""
    from .audio_recorder import AudioRecorder
    from .transcriber import Transcriber

    print("\n🎤 音声ファイルを選択してください...")

    try:
        # 音声ファイルを選択
        import webbrowser
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="音声ファイルを選択",
            filetypes=[
                ("音声ファイル", "*.wav *.mp3 *.m4a *.flac *.ogg"),
                ("すべてのファイル", "*.*"),
            ]
        )

        if not file_path:
            print("  音声ファイルが選択されませんでした")
            return

        print(f"\n📁 ファイル：{file_path}")

        # 音声認識
        recorder = AudioRecorder()
        transcriber = Transcriber()

        try:
            audio, info = recorder.record_audio_from_file(file_path)
            if not audio:
                print("  音声データの読み込みに失敗しました")
                return

            print(f"\n📊 {info}")

            # 音声認識
            print("\n🔄 音声認識中...")
            transcript, metadata = transcriber.transcribe(audio, use_ollama=False)

            if not transcript:
                print("  認識に失敗しました")
                return

            print(f"\n📝 認識結果:")
            print(f"  {transcript}")
            print(f"\n⏱️  単語数：{len(transcript.split())} 語")

        finally:
            recorder.cleanup()

    except Exception as e:
        print(f"エラー：{e}")


def test_mic():
    """マイクテスト"""
    from .audio_recorder import AudioRecorder
    from .transcriber import Transcriber

    print("\n🎤 マイクテストを開始します...")
    print("「完了」と入力するか、または 5 秒後に自動で終了します")

    try:
        recorder = AudioRecorder()
        transcriber = Transcriber()

        # 5 秒間録音
        duration = 5.0
        audio = recorder.record(duration)

        if not audio:
            print("  音声データの録音に失敗しました")
            recorder.cleanup()
            return

        print(f"\n📊 録音情報:")
        print(f"  長さ：{duration:.1f} 秒")

        # 音声認識
        print("\n🔄 音声認識中...")
        transcript, metadata = transcriber.transcribe(audio, use_ollama=False)

        if not transcript:
            print("  認識に失敗しました")
            recorder.cleanup()
            return

        print(f"\n📝 認識結果:")
        print(f"  {transcript}")
        print(f"\n⏱️  単語数：{len(transcript.split())} 語")

        recorder.cleanup()

    except KeyboardInterrupt:
        print("\n  テストを中断しました")
    except Exception as e:
        print(f"エラー：{e}")


def check_ollama():
    """Ollama 接続チェック"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"Ollama が起動していません")
            print("  起動方法：ollama serve &")
            return

        print("\n✅ Ollama 接続正常")
        print(result.stdout)

        # 利用可能なモデル
        if result.stdout:
            available_models = []
            for line in result.stdout.split("\n")[2:]:
                if line.strip():
                    parts = line.split()
                    if parts:
                        available_models.append(parts[0])

            if available_models:
                print(f"\n📦 利用可能なモデル:")
                for model in available_models[:5]:
                    print(f"  - {model}")
                if len(available_models) > 5:
                    print(f"  ... (+{len(available_models) - 5} モデル)")

    except FileNotFoundError:
        print("Ollama がインストールされていません")
        print("  入手方法：https://ollama.ai/download")
    except Exception as e:
        print(f"エラー：{e}")


def check_comfyui():
    """ComfyUI 接続チェック"""
    import urllib.request
    import urllib.error

    comfyui_url = config.get("comfyui_api_url", "http://localhost:8188")

    try:
        req = urllib.request.Request(
            f"{comfyui_url}/system/statistics",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())

            print("\n✅ ComfyUI 接続正常")
            print(f"  実行可能：{data.get('comfyui.server_stats', {}).get('can_execute_node', False)}")
            print(f"  メモリ使用量：{data.get('comfyui.server_stats', {}).get('memory_stats', {}).get('total', 0)}")

    except Exception as e:
        print(f"\nComfyUI 接続エラー：{e}")
        print("ComfyUI の起動:")
        print(f"  cd ..\\ComfyUI")
        print(f"  python main.py")


def main():
    parser = argparse.ArgumentParser(description="AuraWhisper - モデル管理とテスト")

    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # download-models コマンド
    download_parser = subparsers.add_parser(
        "download-models",
        help="Whisper モデルをダウンロード"
    )
    download_parser.add_argument(
        "-m", "--model",
        action="append",
        default=["small", "medium", "large-v3"],
        help="ダウンロードするモデル（複数指定可）"
    )
    download_parser.add_argument(
        "-o", "--output-dir",
        help="モデル保存ディレクトリ"
    )

    # test-audio コマンド
    test_audio_parser = subparsers.add_parser(
        "test-audio",
        help="音声ファイルテスト"
    )

    # test-mic コマンド
    test_mic_parser = subparsers.add_parser(
        "test-mic",
        help="マイクテスト"
    )

    # check-ollama コマンド
    subparsers.add_parser(
        "check-ollama",
        help="Ollama 接続チェック"
    )

    # check-comfyui コマンド
    subparsers.add_parser(
        "check-comfyui",
        help="ComfyUI 接続チェック"
    )

    # status コマンド
    status_parser = subparsers.add_parser(
        "status",
        help="ダウンロード済みモデルのステータス"
    )

    args = parser.parse_args()

    if args.command == "download-models":
        output_dir = args.output_dir
        if output_dir:
            import os
            os.makedirs(output_dir, exist_ok=True)
            models_path = Path(output_dir)
        else:
            models_path = Path(__file__).parent.parent / "models"

        available, missing = download_models()
        print("\n📋 ダウンロード結果:")
        print(f"  ダウンロード済み: {len(available)}")
        print(f"  未ダウンロード: {len(missing)}")

        if missing:
            print(f"\n  未ダウンロード: {', '.join(missing)}")
            print("\n  注意：一部のモデルは大きいため、時間がかかります")
        else:
            print("\n  すべてのモデルがダウンロードされました")

    elif args.command == "test-audio":
        test_audio_file()

    elif args.command == "test-mic":
        test_mic()

    elif args.command == "check-ollama":
        check_ollama()

    elif args.command == "check-comfyui":
        check_comfyui()

    elif args.command == "status":
        all_models = ["tiny", "base", "small", "medium", "large-v3"]
        available, missing = check_models_downloaded(all_models)
        print(f"\n  利用可能なモデル: {len(available)}")
        if missing:
            print(f"  未ダウンロード: {', '.join(missing)}")
        else:
            print("  すべてのモデルがダウンロードされています")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
