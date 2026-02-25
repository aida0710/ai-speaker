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
    proc = subprocess.Popen(
        ["mpg123", "-o", "alsa", "-a", playback_device, "-b", "128", "-q", "-"],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    t_proc = time.time()
    first_chunk = True
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            if first_chunk:
                t_first = time.time()
                print(f"[PERF] mpg123 起動  : {t_proc - t_start:.2f}s")
                print(f"[PERF] 最初のチャンク: {t_first - t_start:.2f}s")
                first_chunk = False
            proc.stdin.write(chunk)
    proc.stdin.close()
    proc.wait()
    print("再生終了")

    # アンプ OFF（再生終了後に少し待ってから切る）
    if amp is not None:
        time.sleep(0.3)
        amp.off()
