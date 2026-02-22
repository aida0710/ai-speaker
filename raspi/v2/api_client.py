"""
API 通信モジュール — raspi/v2
テキスト変換（ASR + LLM）と音声ストリーミング（TTS）を別々のリクエストで処理する。
"""

import json

import requests

from config import API_URL, API_TOKEN


def call_text_api(wav_bytes: bytes, history: list, voice: str) -> dict | None:
    """
    音声と履歴を /text エンドポイントに送り、{transcription, reply} を返す。

    Parameters
    ----------
    wav_bytes : bytes
        送信する WAV 音声データ。
    history : list
        会話履歴 [{role, content}, ...]。
    voice : str
        TTS ボイス名（alloy / echo / fable / onyx / nova / shimmer）。
    """
    print("考え中...")
    try:
        resp = requests.post(
            f"{API_URL}/text",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            files={"audio": ("input.wav", wav_bytes, "audio/wav")},
            data={
                "history": json.dumps(history),
                "voice": voice,
            },
            timeout=60,
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

    return resp.json()


def stream_audio(reply: str, voice: str) -> requests.Response | None:
    """
    /audio エンドポイントに reply を送り、ストリーミングレスポンスを返す。

    Parameters
    ----------
    reply : str
        TTS に変換するテキスト。
    voice : str
        TTS ボイス名（alloy / echo / fable / onyx / nova / shimmer）。
    """
    try:
        resp = requests.post(
            f"{API_URL}/audio",
            headers={
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"reply": reply, "voice": voice},
            timeout=60,
            stream=True,
        )
    except requests.exceptions.ConnectionError:
        print("エラー: サーバーに接続できません。API_URL を確認してください。")
        return None
    except requests.exceptions.Timeout:
        print("エラー: 音声ストリームのタイムアウト。")
        return None

    if not resp.ok:
        print(f"エラー: 音声取得エラー {resp.status_code}: {resp.text}")
        return None

    return resp
