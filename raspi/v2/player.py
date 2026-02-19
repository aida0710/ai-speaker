"""
mp3 再生モジュール — raspi/v2
base64 エンコードされた mp3 をデコードして ffplay で再生する。
"""

import base64
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

    # mpg123 で mp3 再生 → ALSA 経由でアンプに出力
    subprocess.run(
        ["mpg123", "-a", playback_device, "-q", tmp_path],
        check=False,
    )
    print("再生終了")
