import type { FC } from "react";
import type { ChatMessagePart } from "@/types/chat";
import { ChatMarkdown } from "@/components/molecules/ChatMarkdown";
import { ChatThinkingBlock } from "@/components/molecules/ChatThinkingBlock";
import { ChatToolCallBlock } from "@/components/molecules/ChatToolCallBlock";
import { ChatDiffBlock } from "@/components/molecules/ChatDiffBlock";
import { ChatErrorBlock } from "@/components/molecules/ChatErrorBlock";

export interface MessagePartDispatcherProps {
  part: ChatMessagePart;
  isStreaming?: boolean;
}

const MessagePartDispatcher: FC<MessagePartDispatcherProps> = ({
  part,
  isStreaming,
}) => {
  const renderPart = () => {
    switch (part.type) {
      case "text":
        return <ChatMarkdown content={part.content} />;

      case "thinking":
        return (
          <ChatThinkingBlock content={part.content} isStreaming={isStreaming} />
        );

      case "toolCall": {
        const showDiff =
          part.displayType === "diff" && part.output !== undefined;
        return (
          <>
            <ChatToolCallBlock
              toolName={part.toolName}
              state={part.state}
              displayType={part.displayType}
              input={part.input}
              output={part.output}
              error={part.error}
            />
            {showDiff && <ChatDiffBlock diff={part.output!} />}
          </>
        );
      }

      case "error":
        return <ChatErrorBlock message={part.message} />;

      default:
        return (
          <span
            style={{
              color: "var(--chat-text-secondary, #888)",
              fontSize: 12,
              fontFamily: "var(--font-sans)",
            }}
          >
            Unknown message part
          </span>
        );
    }
  };

  return <div style={{ marginBottom: 8 }}>{renderPart()}</div>;
};

MessagePartDispatcher.displayName = "MessagePartDispatcher";

export { MessagePartDispatcher };
