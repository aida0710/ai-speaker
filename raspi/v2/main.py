"""
AI スピーカー v2 — メインループ
- 録音ボタン（GPIO23）: 押している間録音 → 離したら API → 再生
- モードボタン（GPIO24）: タップでモード切り替え（MIC_GAIN ↔ SPEAKER_VOL）
- エンコーダ回転       : 現在モードの値を調整 → OLED 更新
"""

import queue
import socket
import threading
import time

from gpiozero import Button

import config
from recorder   import record_audio
from api_client import call_text_api, stream_audio
from player     import init_amp, play_mp3_stream
from display    import init_display, show_idle, show_recording, show_thinking, show_playing, show_network_error
from encoder    import EncoderManager

_NETWORK_CHECK_INTERVAL = 15   # 秒
_NETWORK_CHECK_HOST     = "1.1.1.1"
_NETWORK_CHECK_PORT     = 53   # DNS ポート（軽量な TCP 疎通確認）
_NETWORK_CHECK_TIMEOUT  = 3


def _check_network() -> bool:
    """1.1.1.1:53 への TCP 接続で疎通を確認する。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(_NETWORK_CHECK_TIMEOUT)
            s.connect((_NETWORK_CHECK_HOST, _NETWORK_CHECK_PORT))
        return True
    except OSError:
        return False


def main():
    print("=== AI スピーカー v2 ===")
    print(f"サーバー: {config.API_URL}")
    print(f"ボイス  : {config.VOICE}")
    print("準備完了。ボタンを押して話しかけてください。\n")

    device      = init_display()
    amp         = init_amp(config.AMP_SD_PIN)
    encoder     = EncoderManager()
    rec_button  = Button(config.BUTTON_REC,  pull_up=True)
    mode_button = Button(config.BUTTON_MODE, pull_up=True)
    history     = []

    # PortAudio/ALSA はメインスレッド以外から open() するとセグフォルトするため、
    # コールバック（gpiozero バックグラウンドスレッド）からはキューに積むだけにして
    # 実際の録音・API 処理はメインスレッドで行う。
    _work: queue.Queue[str] = queue.Queue()

    # ネットワーク状態（バックグラウンドスレッドが更新）
    _net_ok = True

    def _network_watcher():
        """15 秒ごとに疎通確認し、状態変化時にキューで通知する。"""
        nonlocal _net_ok
        while True:
            ok = _check_network()
            if ok != _net_ok:
                _net_ok = ok
                msg = "ネットワーク接続が回復しました" if ok else "ネットワーク接続が切断されました"
                print(msg)
                _work.put("net_changed")
            time.sleep(_NETWORK_CHECK_INTERVAL)

    threading.Thread(target=_network_watcher, daemon=True).start()

    def _current_value():
        if encoder.mode == "MIC_GAIN":
            return encoder.volume_gain
        return encoder.speaker_vol

    def _refresh_idle():
        """_net_ok の状態に応じて idle か network_error を表示する。"""
        if _net_ok:
            show_idle(device, encoder.mode, _current_value())
        else:
            show_network_error(device, encoder.mode, _current_value())

    def on_rec_pressed():
        """録音ボタン押下: メインスレッドへ録音タスクを委譲"""
        _work.put("record")

    def on_mode_pressed():
        """モードボタン押下: モード切り替え"""
        encoder.cycle_mode()
        _work.put("refresh")

    def on_rotated():
        """エンコーダ回転: メインスレッドへ表示更新を委譲"""
        _work.put("refresh")

    def _do_record():
        """録音 → API → 再生（メインスレッドで実行）"""
        show_recording(device, encoder.mode, _current_value())
        wav_bytes = record_audio(rec_button, encoder.volume_gain)

        if wav_bytes is None:
            _refresh_idle()
            return

        t0 = time.time()  # 録音終了、送信開始
        show_thinking(device, encoder.mode, _current_value())

        # Step 1: ASR + LLM
        result = call_text_api(wav_bytes, history, config.VOICE)
        t1 = time.time()

        if result is None:
            _refresh_idle()
            return

        transcription = result.get("transcription", "")
        reply         = result.get("reply", "")

        print(f"  あなた : {transcription}")
        print(f"  AI     : {reply}")

        # history をテキスト確定後すぐに更新
        history.append({"role": "user",      "content": transcription})
        history.append({"role": "assistant",  "content": reply})

        # Step 2: TTS ストリーミング再生
        audio_resp = stream_audio(reply, config.VOICE)
        t2 = time.time()

        if audio_resp is not None:
            show_playing(device, encoder.mode, _current_value())
            play_mp3_stream(audio_resp, config.PLAYBACK_DEVICE, amp)

        t3 = time.time()

        print(f"[PERF] /text API : {t1 - t0:.2f}s")
        print(f"[PERF] /audio API: {t2 - t1:.2f}s")
        print(f"[PERF] 再生      : {t3 - t2:.2f}s")
        print(f"[PERF] 合計(送信→再生終了): {t3 - t0:.2f}s")

        _refresh_idle()

    # gpiozero イベントバインド
    rec_button.when_pressed  = on_rec_pressed
    mode_button.when_pressed = on_mode_pressed

    # エンコーダ回転イベント（EncoderManager 内の _on_rotate 後に表示更新）
    _orig_on_rotate = encoder._on_rotate

    def _on_rotate_with_display():
        _orig_on_rotate()
        on_rotated()

    encoder._encoder.when_rotated = _on_rotate_with_display

    # 初期表示
    _refresh_idle()

    try:
        # メインスレッドでキューを監視し、すべての表示・録音処理を行う
        while True:
            try:
                task = _work.get(timeout=0.1)
            except queue.Empty:
                continue
            if task == "record":
                if not _net_ok:
                    print("ネットワーク未接続のため録音をスキップします")
                    continue
                _do_record()
            elif task in ("refresh", "net_changed"):
                _refresh_idle()
    except KeyboardInterrupt:
        print("\n終了します")


if __name__ == "__main__":
    main()
