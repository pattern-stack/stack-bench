import { StackItem } from "@/components/molecules/StackItem";

interface StackConnectorItem {
  id: string;
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
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
