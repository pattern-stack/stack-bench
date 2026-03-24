import {
  createHighlighter,
  type Highlighter,
  type BundledLanguage,
} from "shiki/bundle/web";

let highlighterPromise: Promise<Highlighter> | null = null;

export function getHighlighter(): Promise<Highlighter> {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({
      themes: ["one-dark-pro"],
      langs: [],
    });
  }
  return highlighterPromise;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function highlightCode(
  code: string,
  lang: string
): Promise<string[]> {
  const h = await getHighlighter();
  const loaded = h.getLoadedLanguages();
  if (!loaded.includes(lang)) {
    await h.loadLanguage(lang as BundledLanguage);
  }
  const { tokens } = h.codeToTokens(code, {
    lang: lang as BundledLanguage,
    theme: "one-dark-pro",
  });
  return tokens.map((lineTokens) =>
    lineTokens
      .map((t) => `<span style="color:${t.color}">${escapeHtml(t.content)}</span>`)
      .join("")
  );
}
