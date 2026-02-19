"""
AI スピーカー v2 — メインループ
- ボタン長押し（0.5s）: 録音 → API → 再生
- ボタン短タップ      : モード切り替え（MIC_GAIN ↔ SPEAKER_VOL）
- エンコーダ回転      : 現在モードの値を調整 → OLED 更新
"""

import time

from gpiozero import Button

import config
from recorder   import record_audio
from api_client import call_api
from player     import play_mp3
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

    # 長押しと短タップを区別するフラグ
    _was_held = False

    def on_held():
        """長押し開始: 録音 → API → 再生"""
        nonlocal _was_held
        _was_held = True

        show_recording(device, encoder.mode, _current_value())
        wav_bytes = record_audio(button, encoder.volume_gain)

        if wav_bytes is None:
            show_idle(device, encoder.mode, _current_value())
            return

        show_thinking(device, encoder.mode, _current_value())
        result = call_api(wav_bytes, history, config.VOICE)

        if result is None:
            show_idle(device, encoder.mode, _current_value())
            return

        transcription = result.get("transcription", "")
        reply         = result.get("reply", "")
        audio_b64     = result.get("audio", "")

        print(f"  あなた : {transcription}")
        print(f"  AI     : {reply}")

        history.append({"role": "user",      "content": transcription})
        history.append({"role": "assistant",  "content": reply})

        if audio_b64:
            show_playing(device, transcription, reply, encoder.mode, _current_value())
            play_mp3(audio_b64, config.PLAYBACK_DEVICE)

        show_idle(device, encoder.mode, _current_value())

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

    # gpiozero イベントバインド
    button.when_held    = on_held
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
        # gpiozero はバックグラウンドスレッドでイベントを処理するため、
        # メインスレッドはスリープで待機するだけでよい
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n終了します")


if __name__ == "__main__":
    main()
