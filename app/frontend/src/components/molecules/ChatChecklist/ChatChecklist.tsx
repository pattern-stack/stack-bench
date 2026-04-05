import type { FC } from "react";
import { Icon } from "@/components/atoms/Icon";

export interface ChecklistItem {
  checked: boolean;
  text: string;
}

export interface ChatChecklistProps {
  items: ChecklistItem[];
}

const ChatChecklist: FC<ChatChecklistProps> = ({ items }) => {
  return (
    <ul className="my-[0.5em] pl-0 list-none font-[family-name:var(--font-sans)]">
      {items.map((item, i) => (
        <li
          key={i}
          className="flex items-start gap-[var(--chat-gap-sm)] mb-[var(--chat-gap-xs)]"
        >
          {item.checked ? (
            <Icon
              name="check-circle"
              size="sm"
              className="text-[var(--chat-success)] shrink-0 mt-[2px]"
            />
          ) : (
            <Icon
              name="circle"
              size="sm"
              className="text-[var(--chat-text-tertiary)] shrink-0 mt-[2px]"
            />
          )}
          <span
            className={
              item.checked
                ? "text-[var(--chat-text-tertiary)]"
                : "text-[var(--chat-text-primary)]"
            }
          >
            {item.text}
          </span>
        </li>
      ))}
    </ul>
  );
};

ChatChecklist.displayName = "ChatChecklist";

export { ChatChecklist };
