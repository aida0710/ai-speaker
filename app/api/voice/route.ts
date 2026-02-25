import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { timingSafeEqual } from "crypto";
import path from "path";
import {
  buildMessages,
  transcribeAudio,
  chatComplete,
  textToSpeechStream,
  defaultVoice,
  type Message,
} from "@/lib/voice-pipeline";

function unauthorized() {
  return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
}

function badRequest(message: string) {
  return NextResponse.json({ error: message }, { status: 400 });
}

// Cache system prompt after first load
let cachedSystemPrompt: string | null = null;

async function getSystemPrompt(): Promise<string> {
  if (cachedSystemPrompt !== null) return cachedSystemPrompt;
  cachedSystemPrompt = await readFile(
    path.join(process.cwd(), "system_prompt.txt"),
    "utf-8"
  );
  return cachedSystemPrompt;
}

export async function POST(req: NextRequest) {
  // Auth: fail closed if API_TOKEN is not configured
  const expectedToken = process.env.API_TOKEN;
  if (!expectedToken) {
    console.error("API_TOKEN environment variable is not set");
    return NextResponse.json(
      { error: "Server misconfiguration" },
      { status: 500 }
    );
  }

  const authHeader = req.headers.get("authorization") ?? "";
  const token = authHeader.startsWith("Bearer ")
    ? authHeader.slice(7)
    : null;

  const tokenValid =
    token !== null &&
    token.length === expectedToken.length &&
    timingSafeEqual(Buffer.from(token), Buffer.from(expectedToken));

  if (!tokenValid) {
    return unauthorized();
  }

  // Parse multipart
  let formData: FormData;
  try {
    formData = await req.formData();
  } catch {
    return badRequest("Invalid multipart form data");
  }

  const audioFile = formData.get("audio");
  if (!audioFile || !(audioFile instanceof File)) {
    return badRequest("Missing audio file");
  }

  const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
  if (audioFile.size > MAX_AUDIO_BYTES) {
    return badRequest("Audio file exceeds 25 MB limit");
  }

  // Parse and validate optional history
  let history: Message[] = [];
  const historyRaw = formData.get("history");
  if (historyRaw && typeof historyRaw === "string") {
    let parsed: unknown;
    try {
      parsed = JSON.parse(historyRaw);
    } catch {
      return badRequest("Invalid history JSON");
    }
    if (
      !Array.isArray(parsed) ||
      !parsed.every(
        (m) =>
          typeof m === "object" &&
          m !== null &&
          (m.role === "user" || m.role === "assistant") &&
          typeof m.content === "string"
      )
    ) {
      return badRequest("Invalid history format");
    }
    history = parsed as Message[];
  }

  // Parse optional voice
  const voiceRaw = formData.get("voice");
  const voice =
    typeof voiceRaw === "string" && voiceRaw ? voiceRaw : defaultVoice();

  try {
    const t0 = performance.now();
    const systemPrompt = await getSystemPrompt();

    // ASR
    const transcription = await transcribeAudio(audioFile);
    const t1 = performance.now();

    // Reject silence / unintelligible audio
    if (!transcription.trim()) {
      return NextResponse.json(
        { error: "No speech detected" },
        { status: 422 }
      );
    }

    // LLM
    const messages = buildMessages(systemPrompt, history, transcription);
    const reply = await chatComplete(messages);
    const t2 = performance.now();

    // TTS (streaming)
    const stream = await textToSpeechStream(reply, voice);
    const t3 = performance.now();

    console.log(
      `[PERF] ASR: ${(t1 - t0).toFixed(0)}ms | LLM: ${(t2 - t1).toFixed(0)}ms | TTS stream start: ${(t3 - t2).toFixed(0)}ms | Total: ${(t3 - t0).toFixed(0)}ms`
    );

    return new Response(stream, {
      headers: {
        "Content-Type": "audio/mpeg",
        "X-Transcription": encodeURIComponent(transcription),
        "X-Reply": encodeURIComponent(reply),
      },
    });
  } catch (err) {
    console.error("Voice pipeline error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
