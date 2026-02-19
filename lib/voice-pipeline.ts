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

export async function textToSpeech(
  text: string,
  voice: string
): Promise<string> {
  const validVoices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"];
  const selectedVoice = validVoices.includes(voice) ? voice : "alloy";

  const response = await openai.audio.speech.create({
    model: "gpt-4o-mini-tts-2025-12-15",
    voice: selectedVoice as
      | "alloy"
      | "echo"
      | "fable"
      | "onyx"
      | "nova"
      | "shimmer",
    input: text,
    response_format: "mp3",
  });

  const buffer = Buffer.from(await response.arrayBuffer());
  return buffer.toString("base64");
}
