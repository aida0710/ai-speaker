"""
ロータリーエンコーダ + モード管理 — raspi/v2

使用部品: RE160F-40E3-20A-24P（2相 A/B 出力、プッシュスイッチなし）
モード切り替えは main.py からボタン短タップで cycle_mode() を呼ぶ。
"""

import subprocess

from gpiozero import RotaryEncoder

from config import (
    ENCODER_CLK,
    ENCODER_DT,
    VOLUME_GAIN_DEFAULT,
    VOLUME_GAIN_MIN,
    VOLUME_GAIN_MAX,
    MIXER_CARD,
)

_MODES = ("MIC_GAIN", "SPEAKER_VOL")

# マイクゲインのステップ倍率（1ステップで ×1.26 ≈ 2dB）
_MIC_GAIN_STEP   = 1.26
# スピーカー音量のステップ（1ステップ = 5%）
_SPEAKER_VOL_STEP = 5


class EncoderManager:
    """
    ロータリーエンコーダの回転を受け取り、
    MIC_GAIN または SPEAKER_VOL を調整する。

    Attributes
    ----------
    volume_gain : float
        現在のマイクゲイン倍率。
    speaker_vol : int
        現在のスピーカー音量（0–100 %）。
    mode : str
        現在の調整対象モード（"MIC_GAIN" or "SPEAKER_VOL"）。
    """

    def __init__(self):
        self._volume_gain: float = VOLUME_GAIN_DEFAULT
        self._speaker_vol: int   = 70
        self._mode_index: int    = 0

        self._encoder = RotaryEncoder(ENCODER_CLK, ENCODER_DT, max_steps=0)
        self._encoder.when_rotated = self._on_rotate

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def volume_gain(self) -> float:
        return self._volume_gain

    @property
    def speaker_vol(self) -> int:
        return self._speaker_vol

    @property
    def mode(self) -> str:
        return _MODES[self._mode_index]

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def cycle_mode(self) -> str:
        """モードを次に切り替えて新しいモード名を返す。"""
        self._mode_index = (self._mode_index + 1) % len(_MODES)
        print(f"モード切替: {self.mode}")
        return self.mode

    # ------------------------------------------------------------------
    # Internal callback
    # ------------------------------------------------------------------

    def _on_rotate(self) -> None:
        """エンコーダ回転時に gpiozero から呼ばれるコールバック。"""
        steps = self._encoder.steps
        self._encoder.steps = 0  # カウンタをリセット
        self.on_rotate(steps)

    def on_rotate(self, steps: int) -> None:
        """
        回転量（正=時計回り、負=反時計回り）に応じて値を更新する。

        Parameters
        ----------
        steps : int
            回転ステップ数（符号付き）。
        """
        if self.mode == "MIC_GAIN":
            if steps > 0:
                self._volume_gain = min(
                    self._volume_gain * (_MIC_GAIN_STEP ** steps),
                    VOLUME_GAIN_MAX,
                )
            elif steps < 0:
                self._volume_gain = max(
                    self._volume_gain / (_MIC_GAIN_STEP ** (-steps)),
                    VOLUME_GAIN_MIN,
                )
            print(f"MIC_GAIN: {self._volume_gain:.2f}x")

        elif self.mode == "SPEAKER_VOL":
            self._speaker_vol = max(
                0,
                min(100, self._speaker_vol + steps * _SPEAKER_VOL_STEP),
            )
            self._apply_speaker_vol()
            print(f"SPEAKER_VOL: {self._speaker_vol}%")

    def _apply_speaker_vol(self) -> None:
        """amixer で実際のスピーカー音量を設定する。"""
        subprocess.run(
            ["amixer", "-c", str(MIXER_CARD), "sset", "Master",
             f"{self._speaker_vol}%"],
            check=False,
            capture_output=True,
        )
