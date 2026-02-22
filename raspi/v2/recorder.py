"""
音声録音モジュール — raspi/v2
ボタンが押されている間録音し、wav バイト列を返す。
"""

import io
import wave

import pyaudio
import numpy as np

from config import (
    DEV_INDEX,
    CHUNK,
    FORMAT,
    CHANNELS,
    RATE,
    START_TRIM_CHUNKS,
    END_TRIM_CHUNKS,
)


def record_audio(button, volume_gain: float) -> bytes | None:
    """
    ボタンが押されている間録音し、wav バイト列を返す。

    Parameters
    ----------
    button : gpiozero.Button
        押下状態を監視するボタンオブジェクト。
    volume_gain : float
        マイク入力に掛けるゲイン倍率。
    """
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

    print("録音中...（ボタンを離すと停止）")

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
            signal = np.frombuffer(data, dtype=np.int16).astype(np.float64)
            signal = np.clip(signal * volume_gain, -32768, 32767)
            frames.append(signal.astype(np.int16).tobytes())
        except IOError:
            pass

    print("録音終了")

    # 終了ノイズ除去
    if len(frames) > END_TRIM_CHUNKS:
        frames = frames[:-END_TRIM_CHUNKS]

    stream.stop_stream()
    stream.close()
    audio.terminate()

    if not frames:
        print("録音データがありません")
        return None

    buf = io.BytesIO()
    wf = wave.open(buf, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()
    return buf.getvalue()
