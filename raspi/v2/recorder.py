"""
音声録音モジュール — raspi/v2
ボタンが押されている間録音し、wav バイト列を返す。
"""

import io
import os
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

# PyAudio をメインスレッドで一度だけ初期化（スレッドセーフ対策）
_devnull = os.open(os.devnull, os.O_WRONLY)
_old_stderr = os.dup(2)
os.dup2(_devnull, 2)
try:
    _audio = pyaudio.PyAudio()
finally:
    os.dup2(_old_stderr, 2)
    os.close(_old_stderr)
    os.close(_devnull)


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
    audio = _audio

    # audio.open() 内でも ALSA がエラーメッセージを stderr に出力するため抑制する
    _devnull2 = os.open(os.devnull, os.O_WRONLY)
    _old_stderr2 = os.dup(2)
    os.dup2(_devnull2, 2)
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
        return None
    finally:
        os.dup2(_old_stderr2, 2)
        os.close(_old_stderr2)
        os.close(_devnull2)

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
