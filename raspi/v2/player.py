"""
mp3 再生モジュール — raspi/v2
ストリーミングレスポンスを mpg123 の stdin にパイプして再生する。
MAX98357A の SD ピンで再生前後にアンプを ON/OFF し、ポップノイズを抑制する。
"""

import subprocess
import time

from gpiozero import DigitalOutputDevice


def init_amp(pin: int) -> DigitalOutputDevice:
    """
    MAX98357A の SD ピンを初期化する（LOW = アンプ OFF）。

    Parameters
    ----------
    pin : int
        SD ピンに接続した GPIO 番号 (BCM)。

    Returns
    -------
    DigitalOutputDevice
        アンプ制御用の出力デバイス。
    """
    amp = DigitalOutputDevice(pin, initial_value=False)
    print(f"アンプ SD ピン (GPIO{pin}) を初期化しました（OFF）")
    return amp


def play_mp3_stream(
    response,
    playback_device: str,
    amp: DigitalOutputDevice | None = None,
) -> None:
    """
    ストリーミングレスポンスの mp3 を mpg123 の stdin にパイプして再生する。

    Parameters
    ----------
    response : requests.Response
        stream=True で取得したストリーミングレスポンス。
    playback_device : str
        ALSA デバイス名（例: "plughw:1,0"）。
    amp : DigitalOutputDevice | None
        MAX98357A の SD ピン制御。None なら制御しない。
    """
    # アンプ ON（安定まで少し待つ）
    if amp is not None:
        amp.on()
        time.sleep(0.05)

    print("再生中...")
    t_start = time.time()

    # プリバッファ: 再生前にデータを蓄えて途切れを防止
    # 目標 16KB だが、TTS 生成が遅い長文では最大 2 秒で打ち切る
    _PRE_BUFFER_BYTES = 16384  # 16KB 目標
    _PRE_BUFFER_TIMEOUT = 2.0  # 秒（長文で待ちすぎを防止）
    pre_buf = bytearray()
    chunks_iter = response.iter_content(chunk_size=8192)
    stream_ended = False

    for chunk in chunks_iter:
        if chunk:
            pre_buf.extend(chunk)
            if len(pre_buf) >= _PRE_BUFFER_BYTES:
                break
            if time.time() - t_start > _PRE_BUFFER_TIMEOUT:
                break
    else:
        stream_ended = True

    if not pre_buf:
        print("再生データなし")
        if amp is not None:
            amp.off()
        return

    t_buffered = time.time()
    print(f"[PERF] プリバッファ : {len(pre_buf) / 1024:.1f}KB in {t_buffered - t_start:.2f}s")

    proc = subprocess.Popen(
        ["mpg123", "-o", "alsa", "-a", playback_device, "-b", "128", "-q", "-"],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    # プリバッファ分を一括書き込み
    proc.stdin.write(pre_buf)

    # 残りをストリーミング
    if not stream_ended:
        for chunk in chunks_iter:
            if chunk:
                proc.stdin.write(chunk)

    proc.stdin.close()
    proc.wait()
    print("再生終了")

    # アンプ OFF（再生終了後に少し待ってから切る）
    if amp is not None:
        time.sleep(0.3)
        amp.off()
