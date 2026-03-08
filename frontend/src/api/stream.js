/**
 * Streaming API client — SSE for token-by-token LLM responses.
 *
 * Usage:
 *   await streamChat("explain this code", "kimi", ["@core/services/chat_service.py"],
 *     (token) => appendToUI(token),
 *     () => markDone()
 *   );
 */

import { API_BASE_URL } from "../config/api";
const BASE = API_BASE_URL;

/**
 * Stream a chat response token by token.
 * @param {string} prompt - The user's prompt
 * @param {string} model - Model to use (kimi, opus, qwen, reasoning, consensus)
 * @param {string[]} mentions - @file/@symbol mentions for context
 * @param {function} onToken - Called with each token string
 * @param {function} onDone - Called when stream completes
 * @param {function} onError - Called on error
 */
export async function streamChat(prompt, model = "kimi", mentions = [], onToken, onDone, onError) {
  try {
    const resp = await fetch(`${BASE}/api/stream/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, model, mentions }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") {
            onDone?.();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.token) onToken(parsed.token);
            if (parsed.error) onError?.(parsed.error);
          } catch {}
        }
      }
    }
    onDone?.();
  } catch (err) {
    onError?.(err.message);
  }
}

/**
 * Stream inline code completion.
 */
export async function streamCompletion(codeBefore, codeAfter, filePath, language, onToken, onDone) {
  try {
    const resp = await fetch(`${BASE}/api/stream/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code_before: codeBefore, code_after: codeAfter, file_path: filePath, language }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") { onDone?.(); return; }
          try {
            const parsed = JSON.parse(data);
            if (parsed.token) onToken(parsed.token);
          } catch {}
        }
      }
    }
    onDone?.();
  } catch {}
}

/**
 * Parse @ mentions from text.
 * @param {string} text - Input text that may contain @file.py or @folder/path
 * @returns {{ cleanText: string, mentions: string[] }}
 */
export function parseMentions(text) {
  const mentions = [];
  const cleanText = text.replace(/@([\w./\-]+)/g, (match, path) => {
    mentions.push(path);
    return "";
  }).trim();
  return { cleanText, mentions };
}

export default { streamChat, streamCompletion, parseMentions };
