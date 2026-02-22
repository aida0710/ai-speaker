import OpenAI from "openai";
import { openai } from "./openai";

export type Message = { role: "user" | "assistant"; content: string };

export function buildMessages(
  systemPrompt: string,
  history: Message[],
  transcription: string
): OpenAI.Chat.ChatCompletionMessageParam[] {
  return [
    { role: "system", content: systemPrompt },
    ...history,
    { role: "user", content: transcription },
  ];
}

export function defaultVoice(): string {
  return process.env.OPENAI_TTS_VOICE ?? "alloy";
}

export async function transcribeAudio(audioFile: File): Promise<string> {
  const response = await openai.audio.transcriptions.create({
    model: "whisper-1",
    file: audioFile,
  });
  return response.text;
}

export async function chatComplete(
  messages: OpenAI.Chat.ChatCompletionMessageParam[]
): Promise<string> {
  const model = process.env.OPENAI_MODEL ?? "gpt-4o-mini";
  const response = await openai.chat.completions.create({
    model,
    messages,
  });
  const choice = response.choices[0];
  if (!choice) {
    throw new Error("LLM returned no choices");
  }
  return choice.message.content ?? "";
}

type TtsVoice =
  | "alloy"
  | "ash"
  | "ballad"
  | "cedar"
  | "coral"
  | "echo"
  | "fable"
  | "marin"
  | "nova"
  | "onyx"
  | "sage"
  | "shimmer"
  | "verse";

const VALID_VOICES: TtsVoice[] = [
  "alloy", "ash", "ballad", "cedar", "coral",
  "echo", "fable", "marin", "nova", "onyx",
  "sage", "shimmer", "verse",
];

function selectVoice(voice: string): TtsVoice {
  return (VALID_VOICES as string[]).includes(voice)
    ? (voice as TtsVoice)
    : "alloy";
}

export async function textToSpeech(
  text: string,
  voice: string
): Promise<string> {
  const response = await openai.audio.speech.create({
    model: "gpt-4o-mini-tts-2025-12-15",
    voice: selectVoice(voice),
    input: text,
    speed: 1.3,
    response_format: "mp3",
  });

  const buffer = Buffer.from(await response.arrayBuffer());
  return buffer.toString("base64");
}

export async function textToSpeechStream(
  text: string,
  voice: string
): Promise<ReadableStream<Uint8Array>> {
  const response = await openai.audio.speech.create({
    model: "gpt-4o-mini-tts-2025-12-15",
    voice: selectVoice(voice),
    input: text,
    speed: 1.3,
    response_format: "mp3",
  });

  return response.body as ReadableStream<Uint8Array>;
}
