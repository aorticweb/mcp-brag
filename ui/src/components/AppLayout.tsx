import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { DataSourcesView } from './DataSourcesView';
import { ConfigView } from './ConfigView';
import { DangerZoneView } from './DangerZoneView';
import { Toast } from './Toast';
import { BackendOfflineError } from './BackendOfflineError';
import { useBackendHealth } from '../contexts/BackendHealthContext';
import { cn } from '../utils';

export const AppLayout: React.FC = () => {
  const [activeView, setActiveView] = useState<'datasources' | 'config' | 'danger'>('datasources');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { isBackendHealthy } = useBackendHealth();

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="flex h-screen bg-background overflow-hidden relative">
      {/* Noise texture overlay for depth */}
      <div className="noise pointer-events-none fixed inset-0 z-50" />

      {/* Glass sidebar */}
      <Sidebar
        activeView={activeView}
        onViewChange={setActiveView}
        isCollapsed={isSidebarCollapsed}
        onCollapsedChange={setIsSidebarCollapsed}
        className={cn(
          'flex-shrink-0 relative z-40 transition-all duration-500',
          mounted ? 'translate-x-0 opacity-100' : '-translate-x-full opacity-0'
        )}
      />

      {/* Main content area with smooth transitions */}
      <main
        className={cn(
          'flex-1 overflow-hidden transition-all duration-500 relative',
          mounted ? 'opacity-100' : 'opacity-0'
        )}
      >
        {/* Subtle background - removed gradient */}
        <div className="absolute inset-0 bg-background" />

        {/* Content wrapper */}
        <div className="relative h-full overflow-auto">
          {!isBackendHealthy ? (
            <BackendOfflineError />
          ) : activeView === 'datasources' ? (
            <DataSourcesView isSidebarCollapsed={isSidebarCollapsed} />
          ) : activeView === 'config' ? (
            <ConfigView isSidebarCollapsed={isSidebarCollapsed} />
          ) : (
            <DangerZoneView isSidebarCollapsed={isSidebarCollapsed} />
          )}
        </div>
      </main>

      {/* Toast notifications */}
      <Toast />
    </div>
  );
};
