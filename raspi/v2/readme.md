# raspi/v2 — ロータリーエンコーダ + OLED モニター版

SSD1306 OLED ディスプレイとロータリーエンコーダを備えた AI スピーカー。
ダイヤルを回してマイクゲイン・スピーカー音量をリアルタイム調整できる。

---

## ハードウェア一覧

| 部品 | 型番（秋月） | 役割 |
|------|------------|------|
| Raspberry Pi Zero W | — | メイン基板 |
| USB マイク（PCM2912A 等） | — | 音声入力 |
| I2S アンプ + スピーカー | — | 音声出力 |
| タクタイルスイッチ × 2 | — | 録音ボタン / モード切替ボタン |
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

## 配線図

```text
OLED (SSD1306 I2C)
  VCC  → Pi 1番ピン  (3.3V)
  GND  → Pi 6番ピン  (GND)
  SDA  → Pi 3番ピン  (GPIO2)
  SCL  → Pi 5番ピン  (GPIO3)

ロータリーエンコーダ (EC12E2430803 + AE-RECNV-3)
  A ピン (CLK) → Pi 11番ピン (GPIO17)
  B ピン (DT)  → Pi 13番ピン (GPIO27)
  COM          → Pi 6番ピン  (GND)
  ※ gpiozero が内部プルアップを自動有効化するため外付け抵抗不要

録音ボタン（タクタイルスイッチ）
  片方     → Pi 16番ピン (GPIO23)
  もう片方  → Pi 6番ピン  (GND)

モード切替ボタン（タクタイルスイッチ）
  片方     → Pi 18番ピン (GPIO24)
  もう片方  → Pi 6番ピン  (GND)
```

## Raspberry Pi Zero W 全ピン対応表

```text
        3.3V  [ 1] [ 2]  5V
   GPIO2(SDA) [ 3] [ 4]  5V
   GPIO3(SCL) [ 5] [ 6]  GND        ← OLED / エンコーダ / ボタン GND
      GPIO4   [ 7] [ 8]  GPIO14(TXD)
         GND  [ 9] [10]  GPIO15(RXD)
     GPIO17   [11] [12]  GPIO18      ← [11] エンコーダ A(CLK)
     GPIO27   [13] [14]  GND
     GPIO22   [15] [16]  GPIO23      ← [16] 録音ボタン
        3.3V  [17] [18]  GPIO24      ← [18] モード切替ボタン
GPIO10(MOSI)  [19] [20]  GND
 GPIO9(MISO)  [21] [22]  GPIO25
GPIO11(SCLK)  [23] [24]  GPIO8(CE0)
         GND  [25] [26]  GPIO7(CE1)
  ID_SD(EEPROM)[27][28]  ID_SC(EEPROM)
      GPIO5   [29] [30]  GND
      GPIO6   [31] [32]  GPIO12
     GPIO13   [33] [34]  GND
     GPIO19   [35] [36]  GPIO16
     GPIO26   [37] [38]  GPIO20
         GND  [39] [40]  GPIO21
```

| 物理ピン | GPIO | 役割 | 接続先 |
|---------|------|------|--------|
| 1 | 3.3V | 電源 | OLED VCC |
| 3 | GPIO2 (SDA) | I2C SDA | OLED SDA |
| 5 | GPIO3 (SCL) | I2C SCL | OLED SCL |
| 6 | GND | GND共通 | OLED GND / エンコーダ COM / ボタン GND |
| 11 | GPIO17 | Encoder CLK (A相) | エンコーダ A ピン |
| 13 | GPIO27 | Encoder DT (B相) | エンコーダ B ピン |
| 16 | GPIO23 | 録音ボタン | タクタイルスイッチ片方 |
| 18 | GPIO24 | モード切替ボタン | タクタイルスイッチ片方 |
| その他 | — | 未使用 | — |

---

## インストール手順

```bash
# システムパッケージ
sudo apt-get update
sudo apt-get install -y \
  python3-numpy python3-gpiozero \
  python3-requests python3-pil mpg123 \
  i2c-tools python3-smbus

# I2C を有効化（未設定の場合）
sudo raspi-config nonint do_i2c 0

# venv を作成して luma.oled をインストール
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install luma.oled python-dotenv
```

OLED の接続確認:

```bash
i2cdetect -y 1
# アドレス 0x3c が表示されれば OK
```

---

## 設定

`.env` ファイルを作成してサーバー情報を設定する（`.env.example` を参照）。

```env
API_URL=http://ai-speaker-theta.vercel.app/api/voice
API_TOKEN=your-secret-token
VOICE=nova
```

---

## 起動方法

### 手動起動

```bash
python3 /home/aida/ai-speaker/raspi/v2/main.py
```

### systemd による自動起動

```bash
sudo cp ~/ai-speaker/raspi/v2/ai-speaker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-speaker
sudo systemctl start ai-speaker
```

### デプロイ（git pull + 再起動）

```bash
~/ai-speaker/raspi/v2/deploy.sh
```

### ログ確認

```bash
journalctl -u ai-speaker -f
```

---

## 操作方法

| 操作 | 動作 |
|------|------|
| 録音ボタンを押す → 離す | 録音 → API 送信 → 音声再生 |
| モード切替ボタンを押す | 調整モード切り替え（MIC_GAIN ↔ SPEAKER_VOL） |
| エンコーダを時計回り | 現在モードの値を増加 |
| エンコーダを反時計回り | 現在モードの値を減少 |

---

## OLED 表示

| 状態 | 顔 | テキスト |
|------|-----|---------|
| 待機中 | `o_o` | エンコーダモード / 値 |
| 録音中 | `O.O` | `* REC *` |
| API 呼び出し中 | `-.-` | `Thinking...` |
| 再生中 | `^w^` | `Talking...` |
| ネットワーク未接続 | `x_x` | `Network Error` |

> ネットワーク未接続時は録音ボタンが無効になる。15 秒ごとに自動で疎通確認を行い、回復次第通常状態に戻る。
