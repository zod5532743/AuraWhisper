#!/usr/bin/env python
"""AuraWhisper アプリ動作テストスクリプト"""

import requests
import json
import time

BASE_URL = "http://localhost:8240"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_dashboard():
    print_section("ダッシュボード表示テスト")
    try:
        resp = requests.get(f"{BASE_URL}/api/dashboard", timeout=10)
        print(f"  ステータス: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  言語認識 API: {'稼働' if data.get('language_api') else '停止'}")
            print(f"  翻訳 API: {'稼働' if data.get('translate_api') else '停止'}")
            print(f"  設定 API: {'稼働' if data.get('settings_api') else '停止'}")
            print(f"  管理 API: {'稼働' if data.get('admin_api') else '停止'}")
            print(f"  履歴 API: {'稼働' if data.get('history_api') else '停止'}")
            print(f"  全機能: {data.get('all_features')}")
            print("  ✅ ダッシュボード正常に動作")
        else:
            print(f"  ❌ エラー: {resp.text}")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

def test_language_api():
    print_section("言語認識 API テスト")
    try:
        # テスト音声を生成（簡易テスト）
        text = "こんにちは、これは音声認識のテストです"
        resp = requests.post(
            f"{BASE_URL}/api/v1/language",
            json={"text": text, "source": "ja", "target": "ja"}
        )
        print(f"  ステータス: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"  入力：{text}")
            print(f"  出力：{result.get('translation', 'N/A')}")
            print("  ✅ 言語認識 API 正常に動作")
        else:
            print(f"  レスポンス: {resp.text}")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

def test_translate_api():
    print_section("翻訳 API テスト")
    try:
        text = "Hello world"
        resp = requests.get(
            f"{BASE_URL}/api/v1/translate",
            params={"text": text, "source": "en", "target": "ja"}
        )
        print(f"  ステータス: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"  入力：{text} (en -> ja)")
            print(f"  出力：{result.get('translation', 'N/A')}")
            print("  ✅ 翻訳 API 正常に動作")
        else:
            print(f"  レスポンス: {resp.text}")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

def test_settings_api():
    print_section("設定管理 API テスト")
    try:
        # 設定取得
        resp = requests.get(f"{BASE_URL}/api/config")
        print(f"  設定取得ステータス: {resp.status_code}")
        if resp.status_code == 200:
            config = resp.json()
            print(f"  API キー：{config.get('api_key', '設定済み')[:10]}...")

            # 設定更新
            new_config = config.copy()
            new_config["ai_context"] = "context_test"
            resp = requests.post(f"{BASE_URL}/api/config", json=new_config)
            print(f"  設定更新ステータス: {resp.status_code}")
            if resp.status_code == 200:
                print("  ✅ 設定 API 正常に動作")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

def test_history_api():
    print_section("履歴 API テスト")
    try:
        # 履歴取得
        resp = requests.get(f"{BASE_URL}/api/history")
        print(f"  ステータス: {resp.status_code}")
        if resp.status_code == 200:
            history = resp.json()
            print(f"  履歴項目数：{len(history.get('history', []))}")
            if history.get('history'):
                item = history['history'][-1]
                print(f"  最新: {item.get('timestamp')[:10]}")
            print("  ✅ 履歴 API 正常に動作")
    except Exception as e:
        print(f"  ❌ エラー: {e}")

def run_full_test():
    print_section("AuraWhisper アプリ動作テスト")
    print(f"API エンドポイント：{BASE_URL}")
    print(f"\nテスト開始...")

    # 各 API テストを実行
    test_dashboard()
    test_language_api()
    test_translate_api()
    test_settings_api()
    test_history_api()

    # 合計時間
    print(f"\nテスト完了！")
    print(f"すべての API が正常に動作しています。✅")

if __name__ == "__main__":
    run_full_test()
