import { SidebarNav } from './SidebarNav';
import { TopBar } from './TopBar';

interface LayoutProps {
  children: React.ReactNode;
  activeNav?: string;
}

export function Layout({ children, activeNav }: LayoutProps) {
  return (
    <div className="flex min-h-screen bg-(--color-bg-dark)">
      <SidebarNav activeItem={activeNav} />
      <div className="flex-1 flex flex-col">
        <TopBar />
        <main className="flex-1 p-8">
          {children}
        </main>
      </div>
    </div>
  );
}