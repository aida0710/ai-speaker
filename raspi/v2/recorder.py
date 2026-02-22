"""
音声録音モジュール — raspi/v2
ボタンが押されている間録音し、wav バイト列を返す。

PyAudio/PortAudio は ARMv6 (Raspberry Pi Zero W) で Pa_OpenStream 内で
セグフォルトするため、arecord (ALSA ユーティリティ) をサブプロセスで
使用することで問題を回避する。
"""

import io
import subprocess
import wave

import numpy as np

from config import (
    DEV_INDEX,
    CHUNK,
    CHANNELS,
    RATE,
)

_BYTES_PER_SAMPLE = 2  # S16_LE = 16bit = 2 bytes
_CHUNK_BYTES = CHUNK * _BYTES_PER_SAMPLE * CHANNELS


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
    proc = subprocess.Popen(
        [
            "arecord",
            "-D", f"plughw:{DEV_INDEX},0",
            "-f", "S16_LE",
            "-r", str(RATE),
            "-c", str(CHANNELS),
            "-t", "raw",
            "-q",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    print("録音中...（ボタンを離すと停止）")

    frames = []
    while button.is_pressed:
        data = proc.stdout.read1(_CHUNK_BYTES)
        if not data:
            break
        if volume_gain != 1.0:
            signal = np.frombuffer(data, dtype=np.int16).astype(np.float64)
            signal = np.clip(signal * volume_gain, -32768, 32767)
            data = signal.astype(np.int16).tobytes()
        frames.append(data)

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    print("録音終了")

    if not frames:
        print("録音データがありません")
        return None

    buf = io.BytesIO()
    wf = wave.open(buf, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(_BYTES_PER_SAMPLE)
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()
    return buf.getvalue()
