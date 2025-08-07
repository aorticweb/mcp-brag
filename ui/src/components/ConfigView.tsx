import React, { useEffect, useState, useMemo, useRef } from 'react';
import { Button } from './ui/button';
import Refresh from './icons/Refresh';
import Edit from './icons/Edit';
import Check from './icons/Check';
import Close from './icons/Close';
import { cn } from '../utils';
import { getManualConfig, postManualConfig } from '../server-client/sdk.gen';
import type { ConfigItem } from '../server-client/types.gen';
import { toast } from 'react-toastify';

interface ConfigViewProps {
  className?: string;
  isSidebarCollapsed?: boolean;
}

export const ConfigView: React.FC<ConfigViewProps> = ({
  className,
  isSidebarCollapsed = false,
}) => {
  const [configs, setConfigs] = useState<Record<string, ConfigItem>>({});
  const [loading, setLoading] = useState(true);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const hasShownFetchErrorRef = useRef(false);

  const fetchConfigs = async () => {
    try {
      setRefreshing(true);
      const response = await getManualConfig();

      if (response.data && 'data' in response.data) {
        setConfigs(response.data.data);
        hasShownFetchErrorRef.current = false; // Reset error flag on successful fetch
      }
    } catch (error) {
      console.error('Failed to fetch configs:', error);
      if (!hasShownFetchErrorRef.current) {
        toast.error('Failed to load configurations', { autoClose: 5000 });
        hasShownFetchErrorRef.current = true;
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  const handleEdit = (key: string, currentValue: unknown) => {
    setEditingKey(key);
    setEditValue(JSON.stringify(currentValue));
  };

  const handleSave = async (key: string) => {
    try {
      let parsedValue: unknown;
      const configType = configs[key]?.type;

      if (configType === 'bool') {
        parsedValue = editValue.toLowerCase() === 'true';
      } else if (configType === 'int' || configType === 'float') {
        parsedValue = Number(editValue);
        if (isNaN(parsedValue as number)) {
          throw new Error('Invalid number value');
        }
      } else if (configType === 'list' || configType === 'dict') {
        parsedValue = JSON.parse(editValue);
      } else {
        parsedValue = editValue.replace(/^["']|["']$/g, '');
      }

      await postManualConfig({
        body: {
          config_name: key as
            | 'INGESTION_PROCESS_MAX_FILE_PATHS'
            | 'CHUNK_CHARACTER_LIMIT'
            | 'SEARCH_CHUNK_CHARACTER_LIMIT'
            | 'SEARCH_CHUNKS_LIMIT'
            | 'SEARCH_PROCESSING_TIMEOUT_SECONDS'
            | 'SEARCH_CONTEXT_EXTENSION_CHARACTERS'
            | 'SEARCH_RESULT_LIMIT',
          config_value: parsedValue as
            | string
            | number
            | boolean
            | Array<unknown>
            | Record<string, unknown>,
        },
      });

      toast.success(`Configuration "${key}" updated successfully`);
      await fetchConfigs();
      setEditingKey(null);
    } catch (error) {
      console.error('Failed to update config:', error);
      toast.error('Failed to update configuration. Please check the value format.', {
        autoClose: 5000,
      });
    }
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const toggleGroupCollapse = (group: string) => {
    setCollapsedGroups((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(group)) {
        newSet.delete(group);
      } else {
        newSet.add(group);
      }
      return newSet;
    });
  };

  const formatValue = (value: unknown, type: string): string => {
    if (value === null || value === undefined) return 'null';

    if (type === 'list' || type === 'dict' || typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }

    return String(value);
  };

  const formatConfigName = (name: string): string => {
    return name
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  const getConfigGroup = (key: string): string => {
    if (key.includes('SEARCH')) return 'Search';
    if (key.includes('AUDIO') || key.includes('WHISPER') || key.includes('PARAKEET'))
      return 'Audio Processing';
    if (key.includes('DOWNLOAD')) return 'Download';
    if (key.includes('EMBEDDER') || key.includes('EMBEDDING') || key.includes('VECTORIZER'))
      return 'Embedding';
    if (key.includes('INGESTION') || key.includes('CHUNK')) return 'Ingestion';
    if (key.includes('BULK_QUEUE')) return 'Queue Management';
    if (key.includes('SQLITE') || key.includes('DB')) return 'Database';
    if (key.includes('INSTRUCTIONS')) return 'System';
    return 'Other';
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      bool: 'bg-accent-success/15 text-accent-success',
      int: 'bg-accent-cool/15 text-accent-cool',
      float: 'bg-primary/10 text-primary',
      str: 'bg-accent-warm/15 text-accent-warm',
      list: 'bg-system-yellow/10 text-system-yellow',
      dict: 'bg-accent-cool/10 text-accent-cool',
    };
    return colors[type] || 'bg-foreground/10 text-foreground-secondary';
  };

  const uniqueTypes = useMemo(() => {
    const types = new Set(Object.values(configs).map((c) => c.type));
    return Array.from(types).sort();
  }, [configs]);

  const filteredAndGroupedConfigs = useMemo(() => {
    const filtered = Object.entries(configs).filter(([key, config]) => {
      const matchesSearch =
        searchQuery === '' ||
        key.toLowerCase().includes(searchQuery.toLowerCase()) ||
        formatConfigName(key).toLowerCase().includes(searchQuery.toLowerCase()) ||
        getConfigGroup(key).toLowerCase().includes(searchQuery.toLowerCase());

      const matchesType = selectedType === 'all' || config.type === selectedType;

      return matchesSearch && matchesType;
    });

    // Group configs by category
    const grouped = filtered.reduce(
      (acc, [key, config]) => {
        const group = getConfigGroup(key);
        if (!acc[group]) {
          acc[group] = [];
        }
        acc[group].push([key, config]);
        return acc;
      },
      {} as Record<string, Array<[string, ConfigItem]>>
    );

    // Sort groups and configs within groups
    const sortedGroups = Object.entries(grouped).sort(([a], [b]) => {
      // Define custom sort order for groups
      const order = [
        'Search',
        'Ingestion',
        'Audio Processing',
        'Embedding',
        'Download',
        'Queue Management',
        'Database',
        'System',
        'Other',
      ];
      return order.indexOf(a) - order.indexOf(b);
    });

    return sortedGroups.map(([group, configs]) => ({
      group,
      configs: configs.sort(([a], [b]) => a.localeCompare(b)),
    }));
  }, [configs, searchQuery, selectedType]);

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center h-full', className)}>
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-foreground-secondary">Loading configurations...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'min-h-screen transition-all duration-300',
        isSidebarCollapsed && 'pl-16',
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight mb-2">Configuration</h1>
          <p className="text-foreground-secondary">Manage application settings and parameters</p>
          <div className="mt-4 p-4 bg-primary/5 border border-primary/20 rounded-lg">
            <p className="text-sm text-foreground-secondary">
              <span className="font-medium">Note:</span> Read-only (frozen) configurations can be
              updated by editing the YAML file specified in the{' '}
              <code className="px-1 py-0.5 bg-background rounded text-xs font-mono">
                CONFIG_FILE
              </code>{' '}
              configuration.
            </p>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <input
                type="text"
                placeholder="Search configurations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                  'w-full h-8 px-3 pl-10 bg-background border border-border rounded-lg',
                  'text-sm placeholder-foreground-tertiary',
                  'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                  'transition-all duration-200'
                )}
              />
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-tertiary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
          </div>

          {/* Type Filter */}
          <div className="flex items-center gap-2">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className={cn(
                'h-8 pl-3 pr-8 bg-background border border-border rounded-lg',
                'text-sm font-medium cursor-pointer appearance-none',
                'hover:bg-background-elevated hover:border-border-strong',
                'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                'transition-all duration-200',
                'bg-[url("data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2012%2012%22%3E%3Cpath%20fill%3D%22%23666%22%20d%3D%22M10.293%203.293%206%207.586%201.707%203.293A1%201%200%200%200%20.293%204.707l5%205a1%201%200%200%200%201.414%200l5-5a1%201%200%201%200-1.414-1.414z%22%2F%3E%3C%2Fsvg%3E")] bg-[length:12px_12px] bg-[right_0.5rem_center] bg-no-repeat'
              )}
            >
              <option value="all">All types</option>
              {uniqueTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>

            <Button onClick={fetchConfigs} disabled={refreshing} variant="outline" size="default">
              <Refresh className={cn('w-4 h-4', refreshing && 'animate-spin')} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="flex items-center gap-6 mb-6 text-sm text-foreground-secondary">
          <span>
            {filteredAndGroupedConfigs.reduce((acc, group) => acc + group.configs.length, 0)}{' '}
            configurations
          </span>
          <span>•</span>
          <span>{Object.values(configs).filter((c) => c.frozen).length} read-only</span>
          <span>•</span>
          <span>{filteredAndGroupedConfigs.length} groups</span>
          {collapsedGroups.size > 0 && (
            <>
              <span>•</span>
              <button
                onClick={() => setCollapsedGroups(new Set())}
                className="text-primary hover:text-primary-hover transition-colors duration-200"
              >
                Expand all
              </button>
            </>
          )}
        </div>

        {/* Configuration List */}
        <div className="space-y-6">
          {filteredAndGroupedConfigs.length > 0 ? (
            filteredAndGroupedConfigs.map(({ group, configs }) => (
              <div
                key={group}
                className="bg-background border border-border rounded-xl overflow-hidden"
              >
                {/* Group Header */}
                <button
                  className="w-full px-6 py-3 bg-background-elevated border-b border-border hover:bg-background-elevated/80 transition-colors duration-200"
                  onClick={() => toggleGroupCollapse(group)}
                >
                  <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-foreground flex items-center gap-2">
                      {group}
                      <span className="text-sm font-normal text-foreground-secondary">
                        ({configs.length})
                      </span>
                    </h2>
                    <svg
                      className={cn(
                        'w-5 h-5 text-foreground-secondary transition-transform duration-200',
                        collapsedGroups.has(group) && 'rotate-180'
                      )}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </button>

                {/* Group Configs */}
                {!collapsedGroups.has(group) && (
                  <div className="divide-y divide-border">
                    {configs.map(([key, config]) => {
                      const isEditing = editingKey === key;
                      const isHovered = hoveredRow === key;

                      return (
                        <div
                          key={key}
                          className={cn(
                            'transition-all duration-200',
                            isHovered && 'bg-background-elevated',
                            isEditing && 'bg-primary/5'
                          )}
                          onMouseEnter={() => setHoveredRow(key)}
                          onMouseLeave={() => setHoveredRow(null)}
                        >
                          <div className="px-6 py-4">
                            <div className="flex items-start gap-4">
                              {/* Left Section - Name and Key */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-1">
                                  <h3 className="font-medium text-foreground">
                                    {formatConfigName(key)}
                                  </h3>
                                  <span
                                    className={cn(
                                      'px-2 py-0.5 rounded-full text-xs font-medium',
                                      getTypeColor(config.type)
                                    )}
                                  >
                                    {config.type}
                                  </span>
                                  {config.frozen && (
                                    <span className="px-2 py-0.5 bg-warning/15 text-warning rounded-full text-xs font-medium">
                                      Read-only
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-foreground-tertiary font-mono">{key}</p>
                              </div>

                              {/* Right Section - Value and Actions */}
                              <div className="flex-1 min-w-0">
                                {isEditing ? (
                                  <div className="space-y-3">
                                    <textarea
                                      value={editValue}
                                      onChange={(e) => setEditValue(e.target.value)}
                                      className={cn(
                                        'w-full px-3 py-2 bg-background border border-border rounded-lg',
                                        'font-mono text-sm resize-y',
                                        'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
                                        'transition-all duration-200'
                                      )}
                                      rows={
                                        config.type === 'dict' || config.type === 'list' ? 4 : 1
                                      }
                                      autoFocus
                                    />
                                    <div className="flex gap-2 justify-end">
                                      <Button onClick={handleCancel} variant="ghost" size="sm">
                                        <Close className="w-4 h-4" />
                                        Cancel
                                      </Button>
                                      <Button
                                        onClick={() => handleSave(key)}
                                        variant="default"
                                        size="sm"
                                      >
                                        <Check className="w-4 h-4" />
                                        Save
                                      </Button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="flex items-start gap-3">
                                    <pre
                                      className={cn(
                                        'flex-1 text-sm font-mono text-foreground/85',
                                        'bg-background-tertiary/50 px-3 py-2 rounded-lg',
                                        'overflow-x-auto border border-border/50'
                                      )}
                                    >
                                      {formatValue(config.value, config.type)}
                                    </pre>
                                    {!config.frozen && (
                                      <Button
                                        onClick={() => handleEdit(key, config.value)}
                                        variant="ghost"
                                        size="sm"
                                        className={cn(
                                          'opacity-0 transition-opacity duration-200',
                                          isHovered && 'opacity-100'
                                        )}
                                      >
                                        <Edit className="w-4 h-4" />
                                      </Button>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="bg-background border border-border rounded-xl overflow-hidden">
              <div className="px-6 py-16 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary/10 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-primary"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold mb-2">No configurations found</h3>
                <p className="text-sm text-foreground-secondary">
                  {searchQuery || selectedType !== 'all'
                    ? 'Try adjusting your filters'
                    : 'Configuration settings will appear here'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
