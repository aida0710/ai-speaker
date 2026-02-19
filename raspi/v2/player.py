"""
mp3 再生モジュール — raspi/v2
base64 エンコードされた mp3 をデコードして ffplay で再生する。
"""

import base64
import os
import subprocess
import tempfile


def play_mp3(audio_b64: str, playback_device: str) -> None:
    """
    base64 mp3 をデコードして再生する。

    Parameters
    ----------
    audio_b64 : str
        base64 エンコードされた mp3 データ。
    playback_device : str
        ALSA デバイス名（例: "plughw:1,0"）。
    """
    print("再生中...")
    mp3_bytes = base64.b64decode(audio_b64)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(mp3_bytes)
        tmp_path = f.name

    # ffplay で mp3 再生 → 先頭無音をリアルタイムスキップ
    env = os.environ.copy()
    env["SDL_AUDIODRIVER"] = "alsa"
    env["AUDIODEV"] = playback_device
    subprocess.run(
        [
            "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
            "-af", "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,atempo=1.3",
            tmp_path,
        ],
        env=env,
        check=False,
    )
    print("再生終了")
