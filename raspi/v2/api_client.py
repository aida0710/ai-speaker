"""
API 通信モジュール — raspi/v2
/voice 統合エンドポイントで ASR → LLM → TTS を 1 リクエストで処理する。
レスポンスヘッダに transcription / reply を返し、ボディは MP3 ストリーム。
requests.Session で TCP/TLS 接続を再利用する。
"""

import json
import urllib.parse

import requests

from config import API_URL, API_TOKEN

_session = requests.Session()
_session.headers["Authorization"] = f"Bearer {API_TOKEN}"


def warm_connection():
    """起動時に HEAD リクエストで TLS 接続を確立し、初回レイテンシを削減する。"""
    try:
        _session.head(API_URL, timeout=10)
        print("接続プリウォーム完了")
    except Exception as e:
        print(f"プリウォーム失敗（初回リクエストで接続します）: {e}")


def call_voice_api(
    audio_bytes: bytes, history: list, voice: str
) -> tuple[str, str, requests.Response] | None:
    """
    /voice エンドポイントに音声を送り、ASR→LLM→TTS を 1 往復で処理する。

    Returns
    -------
    (transcription, reply, response) or None on error.
    response はストリーミング MP3 ボディ。
    """
    print("考え中...")
    try:
        resp = _session.post(
            API_URL,
            files={"audio": ("input.wav", audio_bytes, "audio/wav")},
            data={
                "history": json.dumps(history),
                "voice": voice,
            },
            timeout=60,
            stream=True,
        )
    except requests.exceptions.ConnectionError:
        print("エラー: サーバーに接続できません。API_URL を確認してください。")
        return None
    except requests.exceptions.Timeout:
        print("エラー: サーバーからの応答がタイムアウトしました。")
        return None

    if resp.status_code == 401:
        print("エラー: 認証失敗。API_TOKEN を確認してください。")
        return None
    if resp.status_code == 422:
        print("（音声が聞き取れませんでした）")
        return None
    if not resp.ok:
        print(f"エラー: サーバーエラー {resp.status_code}: {resp.text}")
        return None

    transcription = urllib.parse.unquote(resp.headers.get("X-Transcription", ""))
    reply = urllib.parse.unquote(resp.headers.get("X-Reply", ""))

    return transcription, reply, resp
