# raspi/v2 — ロータリーエンコーダ + OLED モニター版

v1 クライアント（`client.py`）に SSD1306 OLED ディスプレイとロータリーエンコーダを追加したバージョン。
ダイヤルを回してマイクゲイン・スピーカー音量をリアルタイム調整できる。

---

## ハードウェア一覧

| 部品 | 型番（秋月） | 役割 |
|------|------------|------|
| Raspberry Pi Zero W | — | メイン基板 |
| USB マイク（PCM2912A 等） | — | 音声入力 |
| I2S アンプ + スピーカー | — | 音声出力 |
| タクタイルスイッチ | — | 録音トリガー / モード切替 |
| OLED 128×64 (SSD1306 I2C) | g112031 | ステータス表示 |
| ロータリーエンコーダ 2相 A/B（ノンクリック）| g106358 (EC12E2430803) | ゲイン / 音量調整 |
| エンコーダ DIP 化基板 | g107241 (AE-RECNV-3) | 2.5mm→2.54mm 変換（ブレッドボード用）|

### ロータリーエンコーダについての注意

秋月 **g118291**（RK09L 可変抵抗 1kΩ B カーブ）は**アナログ可変抵抗**です。
Raspberry Pi Zero W は ADC（アナログ-デジタルコンバータ）を搭載していないため、
追加の ADC IC（MCP3208 等）なしでは直接接続できません。

本実装では**デジタル型ロータリーエンコーダ**（CLK/DT の 2 相パルス出力）を使用します。
代替として以下を推奨します。

| 部品名 | 型番（秋月） | 備考 |
|--------|------------|------|
| RE160F-40E3-20A-24P | **g100292** | 2相A/B出力、プッシュSWなし ✓ |
| EC12E2420801 | g106119 | 2相A/B出力 + プッシュSW付き |

---

## GPIO ピンアサイン

| 物理ピン | GPIO | 役割 | 接続先 |
|---------|------|------|-------|
| 1 | 3.3V | VCC | OLED VCC |
| 3 | 2 (SDA) | I2C SDA | OLED SDA |
| 5 | 3 (SCL) | I2C SCL | OLED SCL |
| 6 | GND | GND | OLED GND、エンコーダ COM(GND) |
| 11 | 17 | Encoder CLK (A相) | エンコーダ A ピン |
| 13 | 27 | Encoder DT (B相) | エンコーダ B ピン |
| 16 | 23 | Button | タクタイルスイッチ（もう片方は GND） |

> RE160F-40E3-20A-24P はプッシュスイッチなしのため GPIO 22 は未使用。

---

## 配線図（テキスト）

```
OLED (SSD1306 I2C)
  VCC  → Pi 1番ピン (3.3V)
  GND  → Pi 6番ピン (GND)
  SDA  → Pi 3番ピン (GPIO2)
  SCL  → Pi 5番ピン (GPIO3)

ロータリーエンコーダ (EC12E2430803 + AE-RECNV-3)
  A ピン → Pi 11番ピン (GPIO17)
  B ピン → Pi 13番ピン (GPIO27)
  COM   → Pi 6番ピン (GND)
  ※ gpiozero が内部プルアップを自動有効化するため外付け抵抗不要

タクタイルスイッチ
  片方  → Pi 16番ピン (GPIO23)
  もう片方 → GND
```

---

## インストール手順

```bash
# システムパッケージ
sudo apt-get update
sudo apt-get install -y \
  python3-pyaudio python3-numpy python3-gpiozero \
  python3-requests python3-pil mpg123 \
  i2c-tools python3-smbus

# I2C を有効化（未設定の場合）
sudo raspi-config nonint do_i2c 0

# venv を作成して luma.oled をインストール
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install luma.oled
```

OLED の接続確認:

```bash
i2cdetect -y 1
# アドレス 0x3c が表示されれば OK
```

---

## 設定

`config.py` を編集してサーバー情報を設定する。

```python
API_URL   = "http://192.168.1.x:3000/api/voice"  # サーバーの IP に変更
API_TOKEN = "your-secret-token"                    # サーバーの API_TOKEN と一致させる
VOICE     = "nova"                                 # TTS ボイス
```

---

## 起動方法

```bash
source venv/bin/activate
python3 raspi/v2/main.py
```

### 操作方法

| 操作 | 動作 |
|------|------|
| ボタン長押し（0.5s 以上）→ 離す | 録音 → API 送信 → 音声再生 |
| ボタン短タップ | 調整モード切り替え（MIC_GAIN ↔ SPEAKER_VOL） |
| エンコーダを時計回り | 現在モードの値を増加 |
| エンコーダを反時計回り | 現在モードの値を減少 |

### OLED 表示

| 状態 | 表示内容 |
|------|---------|
| 待機中 | Ready / 現在モード / 現在値 |
| 録音中 | RECORDING / Release to stop |
| API 呼び出し中 | Thinking... |
| 再生中 | Playing... / 発話と返答の冒頭 |
