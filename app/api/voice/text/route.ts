import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { timingSafeEqual } from "crypto";
import path from "path";
import {
  buildMessages,
  transcribeAudio,
  chatComplete,
  type Message,
} from "@/lib/voice-pipeline";

function unauthorized() {
  return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
}

function badRequest(message: string) {
  return NextResponse.json({ error: message }, { status: 400 });
}

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

  try {
    const systemPrompt = await getSystemPrompt();

    const transcription = await transcribeAudio(audioFile);

    if (!transcription.trim()) {
      return NextResponse.json(
        { error: "No speech detected" },
        { status: 422 }
      );
    }

    const messages = buildMessages(systemPrompt, history, transcription);
    const reply = await chatComplete(messages);

    return NextResponse.json({ transcription, reply });
  } catch (err) {
    console.error("Voice text pipeline error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
