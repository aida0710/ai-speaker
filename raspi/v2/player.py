"""
mp3 再生モジュール — raspi/v2
ストリーミングレスポンスを mpg123 の stdin にパイプして再生する。
"""

import subprocess


def play_mp3_stream(response, playback_device: str) -> None:
    """
    ストリーミングレスポンスの mp3 を mpg123 の stdin にパイプして再生する。

    Parameters
    ----------
    response : requests.Response
        stream=True で取得したストリーミングレスポンス。
    playback_device : str
        ALSA デバイス名（例: "plughw:1,0"）。
    """
    print("再生中...")
    proc = subprocess.Popen(
        ["mpg123", "-o", "alsa", "-a", playback_device, "-q", "-"],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            proc.stdin.write(chunk)
    proc.stdin.close()
    proc.wait()
    print("再生終了")
