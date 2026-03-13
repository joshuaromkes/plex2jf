import type { ReactNode } from 'react';

interface PageWrapperProps {
  children: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function PageWrapper({ children, title, description, action }: PageWrapperProps) {
  return (
    <div className="flex-1 min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="bg-bg-secondary border-b border-bg-tertiary px-8 py-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
            {description && (
              <p className="text-text-secondary mt-2">{description}</p>
            )}
          </div>
          {action && <div className="ml-6">{action}</div>}
        </div>
      </header>

      {/* Content */}
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}

export default PageWrapper;