import { type FC, type ReactNode } from "react";
import { ChatCodeBlock } from "@/components/atoms/ChatCodeBlock";
import { ChatInlineCode } from "@/components/atoms/ChatInlineCode";

export interface ChatMarkdownProps {
  content: string;
}

/**
 * Split content into fenced code blocks and text segments.
 * Handles incomplete/streaming blocks gracefully — an unclosed fence
 * is treated as a still-growing code block.
 */
function splitByCodeBlocks(
  content: string
): Array<{ type: "text" | "code"; value: string; language?: string }> {
  const segments: Array<{
    type: "text" | "code";
    value: string;
    language?: string;
  }> = [];

  const fencePattern = /^```(\w*)\s*$/gm;
  let lastIndex = 0;
  let openFence: { language: string; start: number } | null = null;

  let match: RegExpExecArray | null;
  while ((match = fencePattern.exec(content)) !== null) {
    if (openFence === null) {
      // Opening fence — push preceding text
      const text = content.slice(lastIndex, match.index);
      if (text) segments.push({ type: "text", value: text });
      openFence = {
        language: match[1] || "",
        start: match.index + match[0].length + 1, // skip newline
      };
    } else {
      // Closing fence — push code block
      const code = content.slice(openFence.start, match.index);
      segments.push({
        type: "code",
        value: code.replace(/\n$/, ""),
        language: openFence.language || undefined,
      });
      openFence = null;
    }
    lastIndex = match.index + match[0].length + 1;
  }

  // Handle unclosed fence (streaming) — render what we have as a code block
  if (openFence !== null) {
    const code = content.slice(openFence.start);
    segments.push({
      type: "code",
      value: code.replace(/\n$/, ""),
      language: openFence.language || undefined,
    });
  } else {
    // Remaining text after last fence
    const remaining = content.slice(lastIndex);
    if (remaining) segments.push({ type: "text", value: remaining });
  }

  return segments;
}

/**
 * Parse inline markdown elements: bold, italic, inline code, links.
 */
function parseInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  // Order matters: code first (to avoid interpreting bold/italic inside code),
  // then bold, italic, links.
  const inlinePattern =
    /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)|(_[^_]+_)|(\[[^\]]+\]\([^)]+\))/g;

  let lastIdx = 0;
  let m: RegExpExecArray | null;
  let key = 0;

  while ((m = inlinePattern.exec(text)) !== null) {
    // Push text before match
    if (m.index > lastIdx) {
      nodes.push(text.slice(lastIdx, m.index));
    }

    const full = m[0];
    if (m[1]) {
      // Inline code
      nodes.push(
        <ChatInlineCode key={key++}>{full.slice(1, -1)}</ChatInlineCode>
      );
    } else if (m[2]) {
      // Bold **text**
      nodes.push(<strong key={key++}>{full.slice(2, -2)}</strong>);
    } else if (m[3]) {
      // Italic *text*
      nodes.push(<em key={key++}>{full.slice(1, -1)}</em>);
    } else if (m[4]) {
      // Italic _text_
      nodes.push(<em key={key++}>{full.slice(1, -1)}</em>);
    } else if (m[5]) {
      // Link [text](url)
      const linkMatch = full.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        nodes.push(
          <a
            key={key++}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--chat-agent)] no-underline hover:underline"
          >
            {linkMatch[1]}
          </a>
        );
      }
    }
    lastIdx = m.index + full.length;
  }

  // Remaining text
  if (lastIdx < text.length) {
    nodes.push(text.slice(lastIdx));
  }

  return nodes;
}

/**
 * Parse a text segment (non-code-block) into block-level elements:
 * headings, lists, paragraphs.
 */
function parseTextBlock(text: string, baseKey: number): ReactNode[] {
  const elements: ReactNode[] = [];
  const lines = text.split("\n");
  let key = baseKey;

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // Skip empty lines
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Headers
    const h3Match = line.match(/^###\s+(.*)/);
    if (h3Match) {
      elements.push(
        <h3
          key={key++}
          className="text-[1.1em] font-bold text-[var(--chat-text-secondary)] my-[0.3em] mt-[0.6em] font-[family-name:var(--font-sans)]"
        >
          {parseInline(h3Match[1])}
        </h3>
      );
      i++;
      continue;
    }

    const h2Match = line.match(/^##\s+(.*)/);
    if (h2Match) {
      elements.push(
        <h2
          key={key++}
          className="text-[1.2em] font-bold text-[var(--chat-text-primary)] my-[0.3em] mt-[0.6em] font-[family-name:var(--font-sans)]"
        >
          {parseInline(h2Match[1])}
        </h2>
      );
      i++;
      continue;
    }

    const h1Match = line.match(/^#\s+(.*)/);
    if (h1Match) {
      elements.push(
        <h1
          key={key++}
          className="text-[1.4em] font-bold text-[var(--chat-text-primary)] my-[0.3em] mt-[0.6em] font-[family-name:var(--font-sans)]"
        >
          {parseInline(h1Match[1])}
        </h1>
      );
      i++;
      continue;
    }

    // Unordered list
    if (/^\s*[-*+]\s+/.test(line)) {
      const items: ReactNode[] = [];
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        const itemText = lines[i].replace(/^\s*[-*+]\s+/, "");
        items.push(<li key={key++}>{parseInline(itemText)}</li>);
        i++;
      }
      elements.push(
        <ul
          key={key++}
          className="my-[0.5em] pl-[1.5em] font-[family-name:var(--font-sans)]"
        >
          {items}
        </ul>
      );
      continue;
    }

    // Ordered list
    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items: ReactNode[] = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
        const itemText = lines[i].replace(/^\s*\d+[.)]\s+/, "");
        items.push(<li key={key++}>{parseInline(itemText)}</li>);
        i++;
      }
      elements.push(
        <ol
          key={key++}
          className="my-[0.5em] pl-[1.5em] font-[family-name:var(--font-sans)]"
        >
          {items}
        </ol>
      );
      continue;
    }

    // Blockquote
    if (/^>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        quoteLines.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      elements.push(
        <blockquote
          key={key++}
          className="my-[0.5em] ml-[var(--chat-gap-sm)] pl-[var(--chat-gap-md)] py-[var(--chat-gap-xs)] border-l-[length:var(--chat-tool-border-width)] border-l-[var(--chat-warning)] bg-[var(--chat-bg-message)] rounded-r-[var(--chat-radius)] font-[family-name:var(--font-sans)] text-[var(--chat-text-secondary)]"
        >
          {parseInline(quoteLines.join(" "))}
        </blockquote>
      );
      continue;
    }

    // Paragraph — collect consecutive non-empty, non-special lines
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^#{1,3}\s/.test(lines[i]) &&
      !/^\s*[-*+]\s+/.test(lines[i]) &&
      !/^\s*\d+[.)]\s+/.test(lines[i]) &&
      !/^>\s?/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      elements.push(
        <p
          key={key++}
          className="my-[0.5em] font-[family-name:var(--font-sans)]"
        >
          {parseInline(paraLines.join(" "))}
        </p>
      );
    }
  }

  return elements;
}

const ChatMarkdown: FC<ChatMarkdownProps> = ({ content }) => {
  const segments = splitByCodeBlocks(content);
  let keyCounter = 0;

  const children: ReactNode[] = [];

  for (const segment of segments) {
    if (segment.type === "code") {
      children.push(
        <ChatCodeBlock
          key={keyCounter++}
          code={segment.value}
          language={segment.language}
        />
      );
    } else {
      children.push(...parseTextBlock(segment.value, keyCounter));
      // Advance key counter past however many elements were added
      keyCounter += 1000;
    }
  }

  return (
    <div className="leading-[1.6] text-[var(--chat-text-primary)] font-[family-name:var(--font-sans)]">
      {children}
    </div>
  );
};

ChatMarkdown.displayName = "ChatMarkdown";

export { ChatMarkdown };
