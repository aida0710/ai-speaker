# Voice API Design — 2026-02-19

## 概要

Raspberry Pi上で動作するAIスピーカー向けのREST API。
音声を受け取り、ASR → LLM → TTSパイプラインで処理し、音声レスポンスを返す。

## アーキテクチャ

Next.js App Router の Route Handler (`/api/voice`) として実装。
OpenAI APIを使ってASR/LLM/TTSをすべて処理する。

## エンドポイント

```
POST /api/voice
Authorization: Bearer <API_TOKEN>
Content-Type: multipart/form-data
```

### リクエストフィールド

| フィールド | 必須 | 型     | 説明 |
|----------|------|--------|------|
| audio    | 必須 | File   | 音声ファイル (wav/mp3/webm等、Whisper対応形式) |
| history  | 任意 | string | JSON配列 `[{role, content}, ...]` 会話履歴 |
| voice    | 任意 | string | TTS voice: alloy/echo/fable/onyx/nova/shimmer |

### レスポンス (200 OK)

```json
{
  "transcription": "ユーザーの発話テキスト",
  "reply": "LLMの返答テキスト",
  "audio": "<base64エンコードされたmp3>"
}
```

### エラーレスポンス

| コード | 説明 |
|--------|------|
| 401    | `{ "error": "Unauthorized" }` — トークン不正 |
| 400    | `{ "error": "..." }` — リクエスト不正 |
| 500    | `{ "error": "..." }` — サーバーエラー |

## データフロー

```
Raspi → [audio + history + voice?] → POST /api/voice
                                              ↓
                                      認証チェック (Bearer token)
                                              ↓
                                      Whisper API (ASR)
                                      audio → transcription
                                              ↓
                                      GPT API (LLM)
                                      system_prompt.txt + history + transcription
                                              ↓ reply
                                      TTS API
                                      reply → mp3 (base64)
                                              ↓
← { transcription, reply, audio_b64 } ←────────
```

## クライアント側の履歴管理 (Raspi/Python)

```python
history = []

while True:
    # 音声録音 ...
    res = requests.post(
        "http://api-server/api/voice",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        files={"audio": open("rec.wav", "rb")},
        data={
            "history": json.dumps(history),
            "voice": "nova"
        }
    ).json()

    # 履歴を更新
    history.append({"role": "user", "content": res["transcription"]})
    history.append({"role": "assistant", "content": res["reply"]})

    # 音声再生
    play_audio(base64.b64decode(res["audio"]))
```

## ファイル構成

```
app/
  api/
    voice/
      route.ts         ← Route Handler (認証・パイプライン処理)
lib/
  openai.ts            ← OpenAIクライアント初期化
system_prompt.txt      ← LLMのsystem prompt (キャラクター設定等)
.env.local             ← 環境変数
```

## 環境変数

```env
# 必須
OPENAI_API_KEY=sk-...
API_TOKEN=your-secret-token

# オプション (デフォルト値あり)
OPENAI_MODEL=gpt-4o-mini
OPENAI_TTS_VOICE=alloy    # voice未指定時のデフォルト
```

## 技術スタック

- **フレームワーク:** Next.js 16 (App Router)
- **言語:** TypeScript
- **ASR:** OpenAI Whisper API (`whisper-1`)
- **LLM:** OpenAI Chat Completions API
- **TTS:** OpenAI TTS API (`tts-1`)
- **認証:** Bearer token (静的シークレット)