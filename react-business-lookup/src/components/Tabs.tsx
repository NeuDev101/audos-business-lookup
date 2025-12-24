interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  return (
    <div className="flex gap-2 mb-8">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-6 py-3 rounded-lg font-medium transition-colors ${
            activeTab === tab.id
              ? 'bg-(--color-primary) text-white'
              : 'bg-(--color-bg-card) text-(--color-text-secondary) hover:bg-(--color-bg-card-hover)'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}