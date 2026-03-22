import { StackItem } from "@/components/molecules/StackItem";
import type { CIStatus } from "@/types/activity";

interface StackConnectorItem {
  id: string;
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
  prNumber?: number | null;
  ciStatus?: CIStatus;
  needsRestack?: boolean;
}

interface StackConnectorProps {
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

function StackConnector({ items, activeIndex, onSelect }: StackConnectorProps) {
  return (
    <div className="flex flex-col">
      {items.map((item, index) => (
        <StackItem
          key={item.id}
          title={item.title}
          status={item.status}
          additions={item.additions}
          deletions={item.deletions}
          prNumber={item.prNumber}
          ciStatus={item.ciStatus}
          needsRestack={item.needsRestack}
          isActive={index === activeIndex}
          isFirst={index === 0}
          isLast={index === items.length - 1}
          onClick={() => onSelect(index)}
        />
      ))}
    </div>
  );
}

StackConnector.displayName = "StackConnector";

export { StackConnector };
export type { StackConnectorProps, StackConnectorItem };
