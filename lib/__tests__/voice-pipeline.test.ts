import { buildMessages, defaultVoice } from "../voice-pipeline";

describe("buildMessages", () => {
  it("prepends system message from prompt", () => {
    const history = [{ role: "user" as const, content: "hello" }];
    const transcription = "how are you";
    const systemPrompt = "You are a helpful assistant.";

    const messages = buildMessages(systemPrompt, history, transcription);

    expect(messages[0]).toEqual({ role: "system", content: systemPrompt });
    expect(messages[messages.length - 1]).toEqual({
      role: "user",
      content: transcription,
    });
    expect(messages.length).toBe(3); // system + 1 history + new user
  });

  it("works with empty history", () => {
    const messages = buildMessages("system", [], "hi");
    expect(messages.length).toBe(2); // system + user
    expect(messages[0].role).toBe("system");
    expect(messages[1]).toEqual({ role: "user", content: "hi" });
  });
});

describe("defaultVoice", () => {
  it("returns env value when set", () => {
    process.env.OPENAI_TTS_VOICE = "nova";
    expect(defaultVoice()).toBe("nova");
  });

  it("falls back to alloy when env not set", () => {
    delete process.env.OPENAI_TTS_VOICE;
    expect(defaultVoice()).toBe("alloy");
  });
});
