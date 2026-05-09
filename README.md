# 🎙️ AuraWhisper
**Your Voice, Your Data, Your Local AI.**

AuraWhisper は、プライバシーを最優先に考えた、完全ローカル完結型の高性能AI音声入力・推敲ツールです。

---

## 🚀 Download & Install (v1.2.0)
 
今すぐ AuraWhisper を使い始めるには、GitHub リポジトリから最新のコードを取得するか、リリースセクションを確認してください。
 
👉 **[AuraWhisper リリース一覧](https://github.com/zod5532743/AuraWhisper/releases)**
 
*   `AuraWhisper-v1.2.0` (最新リリース版)
*   詳細は [日本語取扱説明書 (USER_GUIDE.md)](./USER_GUIDE.md) または [English User Guide (USER_GUIDE_EN.md)](./USER_GUIDE_EN.md) をご覧ください。

---

## 🌟 プロジェクトの核心: "True Privacy"

AuraWhisper の最大の特徴は、**「すべての処理があなたのPC内で完結する」**ことです。

- **🔒 完全オフライン動作**: インターネット接続は一切不要。音声データやテキストがクラウドに送信されることはありません。
- **🧠 ローカル LLM (Ollama) 搭載**: 高精度な校正・推敲も、ローカルで動作するLLMによって行われます。
- **⚡ 爆速の応答速度**: 通信待ち（レイテンシ）ゼロ。録音終了と同時に AI が動き出します。

---

## ✨ 主要機能

- **✅ プレミアム・グラスモーフィズム UI**: Superwhisper を彷彿とさせる、OSに溶け込む洗練されたデザイン。
- **✅ 有機的な流体ウェーブフォーム**: 音声入力を視覚的に楽しむための、滑らかで美しいアニメーション。
- **✅ シームレスな文字起こし**: OpenAI Whisper を活用した、ローカルでの高精度な音声認識。
- **✅ AI による自動推敲**: Ollama を通じて、文法ミスや話し言葉を瞬時にビジネスレベルの文章へブラッシュアップ。
- **✅ グローバル・ホットキー**: `Alt+Shift+S` (初期設定) で、どのアプリからでも即座に録音を開始。

---

## 🛠️ テクノロジー・スタック

- **Frontend**: Electron, Javascript (Vanilla ES6+), CSS3 (Modern Glassmorphism)
- **Backend**: Python 3.10+, FastAPI
- **AI Core**: 
  - **Speech-to-Text**: [Whisper](https://github.com/openai/whisper)
  - **Text Refinement**: [Ollama](https://ollama.com/) (Local LLM)

---

## 🚀 始め方 (開発者向け)

1. **バックグラウンド・プロセスの起動**:
   Ollama がインストールされ、モデルがダウンロードされていることを確認してください。
2. **依存関係のインストール**:
   ```bash
   npm install
   ```
3. **アプリケーションの起動**:
   ```bash
   npm start
   ```

---

## 🗺️ ロードマップ
Superwhisper を超える体験を目指し、コンテキスト理解の強化や、よりシームレスなアプリ連携を計画しています。詳細は [ROADMAP.md](./ROADMAP.md) を参照してください。

---

## 📄 ライセンス
This project is licensed under the MIT License.
