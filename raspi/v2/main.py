"""
AI スピーカー v2 — メインループ
- ボタン長押し（0.5s）: 録音 → API → 再生
- ボタン短タップ      : モード切り替え（MIC_GAIN ↔ SPEAKER_VOL）
- エンコーダ回転      : 現在モードの値を調整 → OLED 更新
"""

import queue
import time

from gpiozero import Button

import config
from recorder   import record_audio
from api_client import call_text_api, stream_audio
from player     import play_mp3_stream
from display    import init_display, show_idle, show_recording, show_thinking, show_playing
from encoder    import EncoderManager


def main():
    print("=== AI スピーカー v2 ===")
    print(f"サーバー: {config.API_URL}")
    print(f"ボイス  : {config.VOICE}")
    print("準備完了。ボタンを押して話しかけてください。\n")

    device  = init_display()
    encoder = EncoderManager()
    button  = Button(config.BUTTON_PIN, pull_up=True, hold_time=0.5)
    history = []

    # PortAudio/ALSA はメインスレッド以外から open() するとセグフォルトするため、
    # コールバック（gpiozero バックグラウンドスレッド）からはキューに積むだけにして
    # 実際の録音・API 処理はメインスレッドで行う。
    _work: queue.Queue[str] = queue.Queue()

    # 長押しと短タップを区別するフラグ
    _was_held = False

    def on_held():
        """長押し検知: メインスレッドへ録音タスクを委譲"""
        nonlocal _was_held
        _was_held = True
        _work.put("record")

    def on_released():
        """ボタン離し: 長押しでなければモード切り替え"""
        nonlocal _was_held
        if not _was_held:
            new_mode = encoder.cycle_mode()
            show_idle(device, new_mode, _current_value())
        _was_held = False

    def on_rotated():
        """エンコーダ回転: 値更新 → OLED 更新"""
        show_idle(device, encoder.mode, _current_value())

    def _current_value():
        if encoder.mode == "MIC_GAIN":
            return encoder.volume_gain
        return encoder.speaker_vol

    def _do_record():
        """録音 → API → 再生（メインスレッドで実行）"""
        show_recording(device, encoder.mode, _current_value())
        wav_bytes = record_audio(button, encoder.volume_gain)

        if wav_bytes is None:
            show_idle(device, encoder.mode, _current_value())
            return

        show_thinking(device, encoder.mode, _current_value())

        # Step 1: ASR + LLM
        result = call_text_api(wav_bytes, history, config.VOICE)

        if result is None:
            show_idle(device, encoder.mode, _current_value())
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

        if audio_resp is not None:
            show_playing(device, transcription, reply, encoder.mode, _current_value())
            play_mp3_stream(audio_resp, config.PLAYBACK_DEVICE)

        show_idle(device, encoder.mode, _current_value())

    # gpiozero イベントバインド
    button.when_held     = on_held
    button.when_released = on_released

    # エンコーダ回転イベント（EncoderManager 内の _on_rotate 後に表示更新）
    _orig_on_rotate = encoder._on_rotate

    def _on_rotate_with_display():
        _orig_on_rotate()
        on_rotated()

    encoder._encoder.when_rotated = _on_rotate_with_display

    # 初期表示
    show_idle(device, encoder.mode, _current_value())

    try:
        # メインスレッドでキューを監視し、録音タスクを処理する
        while True:
            try:
                task = _work.get(timeout=0.1)
            except queue.Empty:
                continue
            if task == "record":
                _do_record()
    except KeyboardInterrupt:
        print("\n終了します")


if __name__ == "__main__":
    main()
