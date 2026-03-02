/**
 * Inline Code Completion Client
 *
 * Requests completion from the backend as you type.
 * Shows ghost text that can be accepted with Tab.
 */

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Get inline code completion.
 * @param {string} codeBefore - Code before cursor
 * @param {string} codeAfter - Code after cursor
 * @param {string} language - Programming language
 * @param {string} filePath - Current file path
 * @returns {Promise<{completion: string, source: string, latency_ms: number}>}
 */
export async function getCompletion(codeBefore, codeAfter = "", language = "python", filePath = "") {
  try {
    const resp = await fetch(`${BASE}/api/complete/inline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code_before: codeBefore, code_after: codeAfter, language, file_path: filePath }),
    });
    if (!resp.ok) return { completion: "", source: "error" };
    return await resp.json();
  } catch {
    return { completion: "", source: "error" };
  }
}

/**
 * Stream longer completions token by token.
 */
export async function streamCompletion(codeBefore, language, onToken, onDone) {
  try {
    const resp = await fetch(`${BASE}/api/complete/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code_before: codeBefore, language }),
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

export default { getCompletion, streamCompletion };
