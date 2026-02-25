"""
設定定数 — raspi/v2
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env を読み込む（このファイルと同じディレクトリ）
load_dotenv(Path(__file__).parent / ".env")

# --- API ---
API_URL   = os.environ["API_URL"]
API_TOKEN = os.environ["API_TOKEN"]
VOICE     = os.environ.get("VOICE", "nova")

# --- ハードウェア ---
BUTTON_REC  = 23     # 録音ボタン（押している間録音）
BUTTON_MODE = 24     # モード切替ボタン
DEV_INDEX   = 1      # arecord -l で確認したカード番号

# --- 録音設定 ---
# arecord で S16_LE (int16) を使用するため FORMAT 定数は不要
CHUNK    = 4096
CHANNELS = 1
RATE     = 16000

# --- マイクゲイン ---
VOLUME_GAIN_DEFAULT = 16.0
VOLUME_GAIN_MIN     = 1.0
VOLUME_GAIN_MAX     = 128.0

# --- ロータリーエンコーダ ---
ENCODER_CLK = 17   # GPIO17 (物理ピン 11)
ENCODER_DT  = 27   # GPIO27 (物理ピン 13)
ENCODER_SW  = 22   # 未使用（RE160F-40E3-20A-24P はプッシュスイッチなし）

# --- OLED ---
OLED_WIDTH  = 128
OLED_HEIGHT = 64

# --- 再生 ---
PLAYBACK_DEVICE = "plughw:1,0"   # mpg123 -a に渡す ALSA デバイス
MIXER_CARD      = 1              # amixer -c に渡すカード番号
