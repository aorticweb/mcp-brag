import React, { useState, useEffect, useRef } from 'react';
import { cn } from '../utils';
import Document from './icons/Document';
import { Gear } from './icons/Gear';
import { ChevronRight } from './icons/ChevronRight';
import logoSvg from '../images/icon.svg';
import { useBackendHealth } from '../contexts/BackendHealthContext';

interface SidebarItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  shortcut?: string;
}

interface SidebarProps {
  activeView: 'datasources' | 'config';
  onViewChange: (view: 'datasources' | 'config') => void;
  className?: string;
  isCollapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  onViewChange,
  className,
  isCollapsed,
  onCollapsedChange,
}) => {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const [isHoveringCollapse, setIsHoveringCollapse] = useState(false);
  const { isBackendHealthy } = useBackendHealth();
  const sidebarRef = useRef<HTMLDivElement>(null);

  const items: SidebarItem[] = [
    {
      id: 'datasources',
      label: 'Data Sources',
      icon: <Document className="w-5 h-5" />,
      shortcut: '⌘D',
    },
    {
      id: 'config',
      label: 'Configuration',
      icon: <Gear className="w-5 h-5" />,
      shortcut: '⌘,',
    },
  ];

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        switch (e.key) {
          case 'd':
            e.preventDefault();
            onViewChange('datasources');
            break;
          case ',':
            e.preventDefault();
            onViewChange('config');
            break;
          case '[':
            e.preventDefault();
            onCollapsedChange(!isCollapsed);
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCollapsed, onCollapsedChange, onViewChange]);

  return (
    <>
      {/* Expand button when collapsed - minimal and elegant */}
      {isCollapsed && (
        <button
          onClick={() => onCollapsedChange(false)}
          className="fixed top-4 left-4 z-50 group w-10 h-10 rounded-full bg-background-elevated/80 backdrop-blur-md border border-border/50 shadow-sm hover:shadow-md transition-all duration-300 hover:scale-105 active:scale-95"
          aria-label="Expand sidebar"
        >
          <div className="absolute inset-0 rounded-full bg-primary/0 group-hover:bg-primary/10 transition-colors duration-300" />
          <ChevronRight className="w-4 h-4 text-foreground-secondary group-hover:text-foreground absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 transition-colors duration-300" />
        </button>
      )}

      <div
        ref={sidebarRef}
        className={cn(
          'relative transition-all duration-500 ease-out flex-shrink-0 overflow-hidden',
          isCollapsed ? 'w-0' : 'w-72'
        )}
      >
        {/* Main sidebar container */}
        <div
          className={cn(
            'h-full w-72 absolute left-0 top-0 transition-all duration-500 overflow-hidden',
            'bg-background/80 backdrop-blur-xl border-r border-border/50',
            isCollapsed
              ? 'opacity-0 pointer-events-none -translate-x-full'
              : 'opacity-100 translate-x-0',
            className
          )}
        >
          {/* Premium noise texture overlay */}
          <div className="absolute inset-0 opacity-[0.015] pointer-events-none">
            <svg width="100%" height="100%">
              <filter id="noise">
                <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" />
              </filter>
              <rect width="100%" height="100%" filter="url(#noise)" opacity="1" />
            </svg>
          </div>

          {/* Content wrapper */}
          <div className="relative z-10 h-full flex flex-col">
            {/* Header - refined and minimal */}
            <div className="h-20 flex items-center px-6 draggable relative">
              {/* Subtle top border gradient */}
              <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-border/30 to-transparent" />

              <div className="flex items-center gap-4 non-draggable">
                {/* Logo with subtle glow - larger size */}
                <div className="relative group">
                  <div className="absolute inset-0 bg-primary/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 scale-150" />
                  <img
                    src={logoSvg}
                    alt="AI Search MCP"
                    className="w-16 h-16 relative z-10 brightness-110"
                    style={{ filter: 'invert(1) brightness(1.1)' }}
                  />
                </div>

                {/* Title with elegant typography */}
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-foreground tracking-tight leading-tight">
                    AI Search MCP
                  </h2>
                </div>
              </div>

              {/* Collapse button - ultra minimal */}
              <button
                onClick={() => onCollapsedChange(true)}
                onMouseEnter={() => setIsHoveringCollapse(true)}
                onMouseLeave={() => setIsHoveringCollapse(false)}
                className="ml-auto p-1.5 rounded-lg transition-all duration-300 non-draggable group"
                aria-label="Collapse sidebar"
              >
                <div
                  className={cn(
                    'w-5 h-[1.5px] bg-foreground-tertiary/40 transition-all duration-300',
                    'group-hover:bg-foreground-secondary'
                  )}
                />
                <div
                  className={cn(
                    'w-5 h-[1.5px] bg-foreground-tertiary/40 mt-1.5 transition-all duration-300',
                    'group-hover:bg-foreground-secondary',
                    isHoveringCollapse && 'w-3.5'
                  )}
                />
              </button>
            </div>

            {/* Navigation - refined with premium feel */}
            <nav className="flex-1 px-3 py-2">
              {items.map((item, index) => {
                const isActive = activeView === item.id;
                const isHovered = hoveredItem === item.id;

                return (
                  <div key={item.id} className="relative">
                    {/* Separator between items */}
                    {index > 0 && <div className="h-[1px] bg-border/30 mx-3 my-2" />}

                    <button
                      onClick={() => onViewChange(item.id as 'datasources' | 'config')}
                      onMouseEnter={() => setHoveredItem(item.id)}
                      onMouseLeave={() => setHoveredItem(null)}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-3 rounded-lg',
                        'transition-all duration-300 relative group'
                      )}
                    >
                      {/* Background layer */}
                      <div
                        className={cn(
                          'absolute inset-0 rounded-lg transition-all duration-300',
                          isActive
                            ? 'bg-primary/8'
                            : isHovered
                              ? 'bg-white/[0.02]'
                              : 'bg-transparent'
                        )}
                      />

                      {/* Active indicator - subtle left border */}
                      {isActive && (
                        <div className="absolute left-0 top-3 bottom-3 w-[2.5px] bg-primary rounded-full" />
                      )}

                      {/* Icon with refined animation */}
                      <div
                        className={cn(
                          'relative z-10 transition-all duration-300',
                          isActive
                            ? 'text-primary'
                            : 'text-foreground-tertiary group-hover:text-foreground-secondary'
                        )}
                      >
                        {item.icon}
                      </div>

                      {/* Label */}
                      <span
                        className={cn(
                          'font-medium text-base relative z-10 transition-all duration-300 flex-1 text-left',
                          isActive
                            ? 'text-foreground'
                            : 'text-foreground-secondary group-hover:text-foreground'
                        )}
                      >
                        {item.label}
                      </span>

                      {/* Keyboard shortcut */}
                      {item.shortcut && (
                        <span
                          className={cn(
                            'text-xs font-mono relative z-10 transition-all duration-300',
                            isActive || isHovered
                              ? 'text-foreground-tertiary'
                              : 'text-foreground-muted'
                          )}
                        >
                          {item.shortcut}
                        </span>
                      )}
                    </button>
                  </div>
                );
              })}
            </nav>

            {/* Footer - minimal and informative */}
            <div className="px-6 py-4 border-t border-border/30">
              {/* Connection status with premium indicator */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-foreground-tertiary">System</span>
                <div className="flex items-center gap-1.5">
                  <div className="relative">
                    <div
                      className={cn(
                        'w-1.5 h-1.5 rounded-full',
                        isBackendHealthy ? 'bg-success' : 'bg-destructive'
                      )}
                    />
                    {isBackendHealthy && (
                      <div className="absolute inset-0 w-1.5 h-1.5 rounded-full bg-success animate-ping" />
                    )}
                  </div>
                  <span
                    className={cn(
                      'text-xs font-medium',
                      isBackendHealthy ? 'text-success' : 'text-destructive'
                    )}
                  >
                    {isBackendHealthy ? 'Online' : 'Offline'}
                  </span>
                </div>
              </div>

              {/* Version - ultra minimal */}
              <div className="text-xs text-foreground-muted text-center">v1.0.0</div>
            </div>
          </div>
        </div>

        {/* Mobile overlay */}
        {!isCollapsed && (
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-30 lg:hidden"
            onClick={() => onCollapsedChange(true)}
          />
        )}
      </div>
    </>
  );
};
