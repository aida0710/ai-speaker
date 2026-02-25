import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "crypto";
import { textToSpeechStream, defaultVoice } from "@/lib/voice-pipeline";

function unauthorized() {
  return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
}

function badRequest(message: string) {
  return NextResponse.json({ error: message }, { status: 400 });
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

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return badRequest("Invalid JSON body");
  }

  if (
    typeof body !== "object" ||
    body === null ||
    typeof (body as Record<string, unknown>).reply !== "string" ||
    !(body as Record<string, unknown>).reply
  ) {
    return badRequest("Missing or invalid reply field");
  }

  const { reply, voice: voiceRaw } = body as { reply: string; voice?: unknown };
  const voice =
    typeof voiceRaw === "string" && voiceRaw ? voiceRaw : defaultVoice();

  try {
    const t0 = performance.now();
    const stream = await textToSpeechStream(reply, voice);
    const t1 = performance.now();

    console.log(
      `[PERF /audio] TTS stream start: ${((t1 - t0) / 1000).toFixed(2)}s`
    );

    return new Response(stream, {
      headers: { "Content-Type": "audio/mpeg" },
    });
  } catch (err) {
    console.error("Voice audio pipeline error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
