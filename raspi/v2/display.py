"""
OLED 制御モジュール — raspi/v2
luma.oled (SSD1306 I2C) + Pillow でステータスを表示する。
日本語フォントなし・ASCII 表示のみ。

128×64 レイアウト
  y=0..36  : ASCII 顔（状態で表情変化）
  y=37     : 区切り線
  y=40..55 : 状態情報 + エンコーダモード / 値
"""

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

from config import OLED_WIDTH, OLED_HEIGHT

# 状態ごとの顔（口の部分のみ変える）
_FACE_IDLE      = "o_o"   # 待機
_FACE_RECORDING = "O.O"   # 録音中（目を見開く）
_FACE_THINKING  = "-.-"   # 思考中（目を細める）
_FACE_PLAYING   = "^w^"   # 再生中（笑顔）
_FACE_ERROR     = "x_x"   # エラー（故障顔）


def init_display():
    """SSD1306 OLED デバイスを初期化して返す。"""
    serial = i2c(port=1, address=0x3C)
    device = ssd1306(serial, width=OLED_WIDTH, height=OLED_HEIGHT)
    return device


# ------------------------------------------------------------------
# 内部ユーティリティ
# ------------------------------------------------------------------

def _blank_image():
    image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), 0)
    draw = ImageDraw.Draw(image)
    return image, draw


def _font():
    return ImageFont.load_default()


def _cx(draw, text, font) -> int:
    """水平中央の x 座標を返す。"""
    w = int(draw.textlength(text, font=font))
    return (OLED_WIDTH - w) // 2


def _draw_face(draw, font, mouth: str) -> None:
    """
    3行の ASCII 顔を上部中央に描画する。

    顔の形:
        .---.
       ( X.X )
        `---'
    """
    lines = [" .---.", f"( {mouth} )", " `---'"]
    for i, line in enumerate(lines):
        draw.text((_cx(draw, line, font), 2 + i * 12), line, font=font, fill=1)


def _draw_divider(draw) -> None:
    """y=37 に水平区切り線を引く。"""
    draw.line([(0, 37), (OLED_WIDTH - 1, 37)], fill=1)


def _draw_encoder_status(draw, font, mode_name: str, value) -> None:
    """
    エンコーダの現在モードと値を下部に表示する。

    モード表示例（MIC_GAIN 選択時）:
        >MIC<  SPK
          16.0x
    """
    mic_label = ">MIC<" if mode_name == "MIC_GAIN"   else " MIC "
    vol_label = ">VOL<" if mode_name == "SPEAKER_VOL" else " VOL "
    mode_line = f"{mic_label}  {vol_label}"
    draw.text((_cx(draw, mode_line, font), 40), mode_line, font=font, fill=1)

    if mode_name == "MIC_GAIN":
        val_text = f"{value:.1f}x"
    else:
        val_text = f"{value}%"
    draw.text((_cx(draw, val_text, font), 51), val_text, font=font, fill=1)


# ------------------------------------------------------------------
# 公開 API
# ------------------------------------------------------------------

def show_idle(device, mode_name: str, value) -> None:
    """
    待機中の表示。顔は neutral、エンコーダモードと値を表示。

    Parameters
    ----------
    mode_name : "MIC_GAIN" | "SPEAKER_VOL"
    value : float | int  現在の調整値
    """
    image, draw = _blank_image()
    font = _font()

    _draw_face(draw, font, _FACE_IDLE)
    _draw_divider(draw)
    _draw_encoder_status(draw, font, mode_name, value)

    device.display(image)


def show_recording(device, mode_name: str, value) -> None:
    """録音中の表示。顔は wide-eyed、エンコーダ状態も継続表示。"""
    image, draw = _blank_image()
    font = _font()

    _draw_face(draw, font, _FACE_RECORDING)
    _draw_divider(draw)

    rec_text = "* REC *"
    draw.text((_cx(draw, rec_text, font), 40), rec_text, font=font, fill=1)

    # エンコーダモードをコンパクトに右下に表示
    mic_label = ">MIC<" if mode_name == "MIC_GAIN" else " MIC "
    vol_label = ">VOL<" if mode_name == "SPEAKER_VOL" else " VOL "
    sub = f"{mic_label} {vol_label}"
    draw.text((_cx(draw, sub, font), 51), sub, font=font, fill=1)

    device.display(image)


def show_thinking(device, mode_name: str, value) -> None:
    """API 呼び出し中の表示。顔は eyes-closed。"""
    image, draw = _blank_image()
    font = _font()

    _draw_face(draw, font, _FACE_THINKING)
    _draw_divider(draw)

    think_text = "Thinking..."
    draw.text((_cx(draw, think_text, font), 40), think_text, font=font, fill=1)

    mic_label = ">MIC<" if mode_name == "MIC_GAIN" else " MIC "
    vol_label = ">VOL<" if mode_name == "SPEAKER_VOL" else " VOL "
    sub = f"{mic_label} {vol_label}"
    draw.text((_cx(draw, sub, font), 51), sub, font=font, fill=1)

    device.display(image)


def show_network_error(device, mode_name: str, value) -> None:
    """ネットワーク未接続の表示。顔は x_x、"Network Error" を表示。"""
    image, draw = _blank_image()
    font = _font()

    _draw_face(draw, font, _FACE_ERROR)
    _draw_divider(draw)

    err_text = "Network Error"
    draw.text((_cx(draw, err_text, font), 40), err_text, font=font, fill=1)

    mic_label = ">MIC<" if mode_name == "MIC_GAIN" else " MIC "
    vol_label = ">VOL<" if mode_name == "SPEAKER_VOL" else " VOL "
    sub = f"{mic_label} {vol_label}"
    draw.text((_cx(draw, sub, font), 51), sub, font=font, fill=1)

    device.display(image)


def show_playing(device, mode_name: str, value) -> None:
    """再生中の表示。顔は happy、"Talking..." を表示。"""
    image, draw = _blank_image()
    font = _font()

    _draw_face(draw, font, _FACE_PLAYING)
    _draw_divider(draw)

    talk_text = "Talking..."
    draw.text((_cx(draw, talk_text, font), 40), talk_text, font=font, fill=1)

    mic_label = ">MIC<" if mode_name == "MIC_GAIN" else " MIC "
    vol_label = ">VOL<" if mode_name == "SPEAKER_VOL" else " VOL "
    sub = f"{mic_label} {vol_label}"
    draw.text((_cx(draw, sub, font), 51), sub, font=font, fill=1)

    device.display(image)
