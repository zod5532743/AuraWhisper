from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QLabel
)
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import time
import sys
from .audio_recorder import AudioRecorder # 追加したimport


# --- バックエンド処理シミュレーションのためのステートクラス ---

class WorkerSignals(QObject):
    """別スレッドからGUIに情報を送るためのシグナル定義"""
    progress = pyqtSignal(int, str) # (Percentage, Message)
    finished = pyqtSignal(str)      # 処理完了メッセージ
    error = pyqtSignal(str)        # エラーメッセージ

class BackendWorker(QObject):
    """重いバックエンド処理を別スレッドで実行するワーカーオブジェクト"""
    signals = WorkerSignals()

    def __init__(self):
        super().__init__()

    def do_transcription_simulation(self, recording_file_path):
        """
        (シミュレート) 録音ファイルを受け取り、重い文字起こし処理を実行する。
        このメソッド全体が別スレッドで実行されることが重要。
        """
        self.signals.progress.emit(0, "音声ファイルを読み込み中...")
        time.sleep(1) # 擬似的な待機

        # 処理をシミュレート（例：50%まで）
        for i in range(1, 6):
            percent = i * 20
            message = f"文字起こし処理中... (約{percent}%完了)"
            self.signals.progress.emit(percent, message)
            time.sleep(0.5)
        
        final_text = "会議の議事録テキストがここに生成されました。主要な決定事項は[明日、資料をAさんに依頼する]です。"
        self.signals.progress.emit(100, "文字起こしが完了しました。")
        time.sleep(1)
        self.signals.finished.emit(final_text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... (略)
        self.audio_recorder = AudioRecorder() # インスタンス化
        self.recorder_device_index = None # デバイスIDを保持する場所を準備
        
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # 1. コントロールパネル (ボタン群)
        control_layout = QHBoxLayout()
        
        # 録音ボタン（最初は非アクティブ）
        self.record_button = QPushButton("🔴 録音開始")
        self.record_button.clicked.connect(self.start_recording_simulation)
        control_layout.addWidget(self.record_button)

        # 処理開始ボタン
        self.process_button = QPushButton("▶ 文字起こし開始")
        self.process_button.clicked.connect(self.start_transcription)
        control_layout.addWidget(self.process_button)

        control_layout.addWidget(QLabel(" ")) # スペーサー
        
        main_layout.addLayout(control_layout)

        # 2. ステータス/ログ表示エリア
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setText("--- System Initialized. Ready to record. ---")
        main_layout.addWidget(self.log_output)

        # 3. 結果表示エリア (編集可能)
        self.result_area = QTextEdit()
        self.result_area.setPlaceholderText("=== 文字起こし結果が出力されます ===\n（このエリアで内容の校正や編集を行えます）")
        main_layout.addWidget(self.result_area)

        self.setCentralWidget(central_widget)

    # --- イベントハンドラ ---

        def start_recording_simulation(self):
        """録音開始ボタンが押されたときの処理"""
        self.log_output.clear()
        self.log_output.append("--- ✅ 録音フローを開始します。マイクの入力を待機します... ---")
        self.record_button.setEnabled(False)
        self.process_button.setEnabled(False)
        
        # 1. 録音デバイスの初期化とチェック
        try:
            devices = self.audio_recorder.get_input_devices()
            if not devices:
                self.log_output.append("🛑 エラー: 利用可能なマイクデバイスが見つかりません。マイクを接続してください。")
                self.reset_ui()
                return
            
            # デバイスIDを最初のものを使用し、録音器に設定
            self.recorder_device_index = devices[0]['id']
            self.log_output.append(f"✅ デバイス検出成功: {devices[0]['name']}")
            
            # 録音開始
            self.audio_recorder.start_recording()
            self.log_output.append("🟢 録音開始！実際にマイクに話しかけてください。（シミュレーションのため、3秒後に停止します）")

            # 2. 録音のシミュレーション待機
            time.sleep(3)

            # 3. 録音の停止とファイルの生成
            recorded_path = self.audio_recorder.stop_recording()
            if recorded_path:
                self.log_output.append(f"🟢 録音データが正常に取得され、一時ファイルに保存されました: {recorded_path}")
                # 処理が成功したので、次のステップに必要な情報（ファイルパス）を保持
                self.current_recording_path = recorded_path 
                self.log_output.append("\n--- 録音フロー完了。次に【文字起こし開始】を押してください。---")
            else:
                 self.log_output.append("❌ 録音データが空のため、処理を中止します。")
                 self.reset_ui()

        except Exception as e:
            self.log_output.append(f"🛑 録音の実行中に予期せぬエラーが発生しました。詳細: {str(e)}")
            self.reset_ui()

    def start_transcription(self):
        """文字起こし開始ボタンが押されたときの処理"""
        self.log_output.clear()
        self.log_output.append("--- 🟡 文字起こしエンジンにデータを渡します。処理を開始します... ---")
        self.record_button.setEnabled(False)
        self.process_button.setEnabled(False)
        
    def start_transcription(self):
        """文字起こし開始ボタンが押されたときの処理"""
        if not hasattr(self, 'current_recording_path') or not self.current_recording_path:
            self.log_output.append("⚠️ 録音ファイルが準備されていません。先に【録音開始】を行ってください。")
            self.reset_ui()
            return

        self.log_output.clear()
        self.log_output.append("--- 🟡 文字起こしエンジンにデータを渡します。処理を開始します... ---")
        self.record_button.setEnabled(False)
        self.process_button.setEnabled(False)
        
        dummy_file_path = self.current_recording_path # 前回録音したファイルを使用
        
        # WorkerThreadを起動し、重い処理をバックグラウンドに逃がす
        self.thread = QThread()
        self.worker = BackendWorker()
        # WorkerのインスタンスをGUI側のオブジェクトに保持し、終了後にクリーンアップできるようにする
        self.worker.moveToThread(self.thread)
        
        # シグナル接続
        self.thread.started.connect(self.worker.do_transcription_simulation.emit)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.finished.connect(self.handle_transcription_finished)
        self.worker.signals.error.connect(self.handle_error)
        
        self.thread.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.worker.deleteLater)
        
        self.thread.start()
        self.thread.started.emit()
        
        # クリーンアップ用として、一時ファイルパスをリセットするための情報を保持
        self.current_recording_path = None

    # --- スロット (GUI側の応答メソッド) ---

    def update_progress(self, percent, message):
        """別スレッドからの進行度シグナルを受信し、ログを更新する"""
        self.log_output.append(f"[{percent}%] {message}")
        self.log_output.append("------------------------------------")


    def handle_transcription_finished(self, text):
        """文字起こし完了シグナルを受信したときの処理"""
        self.log_output.append("✅ 処理が正常に完了しました。")
        self.result_area.setText(text)
        self.reset_ui()

    def handle_error(self, message):
        """エラーシグナルを受信したときの処理"""
        self.log_output.setStyleSheet("background-color: #ffeeee;")
        self.log_output.append(f"🛑 エラーが発生しました: {message}")
        self.reset_ui()

    def reset_ui(self):
        """UIの状態をリセットする"""
        self.record_button.setEnabled(True)
        self.process_button.setEnabled(True)
        self.log_output.setStyleSheet("")
        self.log_output.append("\n--- ✨ 準備完了。次の録音を行えます。 ---")


if __name__ == '__main__':
    # 仮想環境が設定されていることを前提とします
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())