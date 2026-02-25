"""
音声録音モジュール — raspi/v2
ボタンが押されている間録音し、OPUS (OGG) バイト列を返す。

PyAudio/PortAudio は ARMv6 (Raspberry Pi Zero W) で Pa_OpenStream 内で
セグフォルトするため、arecord (ALSA ユーティリティ) をサブプロセスで
使用することで問題を回避する。
録音後 ffmpeg で raw PCM → OPUS に圧縮し、アップロードサイズを削減する。
"""

import subprocess

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
    ボタンが押されている間録音し、OPUS (OGG) バイト列を返す。

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

    raw_pcm = b"".join(frames)
    proc_enc = subprocess.run(
        [
            "ffmpeg", "-f", "s16le", "-ar", str(RATE), "-ac", str(CHANNELS),
            "-i", "pipe:0", "-c:a", "libopus", "-b:a", "24k",
            "-compression_level", "0", "-application", "voip",
            "-f", "ogg", "pipe:1",
        ],
        input=raw_pcm,
        capture_output=True,
        timeout=10,
    )
    if proc_enc.returncode != 0:
        print(f"ffmpeg エラー: {proc_enc.stderr.decode()}")
        return None
    return proc_enc.stdout
