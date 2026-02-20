"""
AI スピーカー クライアント
- ボタンを押している間録音
- POST /api/voice に送信（ASR → LLM → TTS）
- 返ってきた mp3 を再生
- 会話履歴はクライアント側で保持
"""

import io
import json
import base64
import subprocess
import tempfile
import time

import pyaudio
import wave
import numpy as np
import requests
from gpiozero import Button

# --- 設定 ---
API_URL   = "http://ai-speaker-theta.vercel.app/api/voice"  # サーバーのIPに変更
API_TOKEN = "HGRVxyW2uHbtunpHer77F7a4rYsPmGMQwY64AmHWkkBC96rX2ieejWzMKDKt_CXiK4Pkst58Wpansjxs_BQSV8WgsAeJK-jUzBtY"                    # .env.local の API_TOKEN と一致させる
VOICE     = "alloy"                                 # alloy / echo / fable / onyx / nova / shimmer

# ハードウェア
BUTTON_PIN = 23
DEV_INDEX  = 1       # arecord -l で確認したカード番号

# 録音設定（v4 と同じ）
CHUNK    = 4096
FORMAT   = pyaudio.paInt32
CHANNELS = 1
RATE     = 48000

# ノイズ対策
START_TRIM_CHUNKS = 10
END_TRIM_CHUNKS   = 5
VOLUME_GAIN       = 16.0

# 再生デバイス（aplay 用）
PLAYBACK_DEVICE = "plughw:1,0"

button = Button(BUTTON_PIN, pull_up=True)


def record_audio() -> bytes | None:
    """ボタンが押されている間録音し、wav バイト列を返す。"""
    audio = pyaudio.PyAudio()

    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=DEV_INDEX,
            frames_per_buffer=CHUNK,
        )
    except Exception as e:
        print(f"エラー: マイクが開けません。{e}")
        audio.terminate()
        return None

    print("🔴 録音中...（ボタンを離すと停止）")

    # 開始ノイズ除去
    for _ in range(START_TRIM_CHUNKS):
        try:
            stream.read(CHUNK, exception_on_overflow=False)
        except Exception:
            pass

    frames = []
    while button.is_pressed:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            signal = np.frombuffer(data, dtype=np.int32).astype(np.float64)
            signal = np.clip(signal * VOLUME_GAIN, -2147483648, 2147483647)
            frames.append(signal.astype(np.int32).tobytes())
        except IOError:
            pass

    print("⬛ 録音終了")

    # 終了ノイズ除去
    if len(frames) > END_TRIM_CHUNKS:
        frames = frames[:-END_TRIM_CHUNKS]

    stream.stop_stream()
    stream.close()
    audio.terminate()

    if not frames:
        print("録音データがありません")
        return None

    # wav としてメモリに書き出す
    buf = io.BytesIO()
    wf = wave.open(buf, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()
    return buf.getvalue()


def call_api(wav_bytes: bytes, history: list) -> dict | None:
    """API に音声と履歴を送り、レスポンス dict を返す。"""
    print("考え中...")
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            files={"audio": ("input.wav", wav_bytes, "audio/wav")},
            data={
                "history": json.dumps(history),
                "voice": VOICE,
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


def play_mp3(audio_b64: str) -> None:
    """base64 mp3 をデコードして再生する。"""
    print("再生中...")
    mp3_bytes = base64.b64decode(audio_b64)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(mp3_bytes)
        tmp_path = f.name

    # mpg123 で mp3 再生 → ALSA 固定・デバイス指定
    subprocess.run(
        ["mpg123", "-o", "alsa", "-a", PLAYBACK_DEVICE, "-q", tmp_path],
        check=False,
        stderr=subprocess.DEVNULL,
    )
    print("✅ 再生終了")


def main():
    print(f"サーバー: {API_URL}")
    print(f"ボイス  : {VOICE}")
    print("準備完了。ボタンを押して話しかけてください。\n")

    history = []  # [{role: "user"|"assistant", content: "..."}]

    try:
        while True:
            button.wait_for_press()

            wav_bytes = record_audio()
            if wav_bytes is None:
                time.sleep(0.5)
                continue

            result = call_api(wav_bytes, history)
            if result is None:
                time.sleep(0.5)
                continue

            transcription = result.get("transcription", "")
            reply         = result.get("reply", "")
            audio_b64     = result.get("audio", "")

            print(f"  あなた : {transcription}")
            print(f"  AI     : {reply}")

            # 会話履歴を更新
            history.append({"role": "user",      "content": transcription})
            history.append({"role": "assistant",  "content": reply})

            if audio_b64:
                play_mp3(audio_b64)

            # チャタリング防止
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n終了します")


if __name__ == "__main__":
    main()
