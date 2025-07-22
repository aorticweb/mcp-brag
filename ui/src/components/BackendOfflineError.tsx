import React from 'react';
import { cn } from '../utils';
import { useBackendHealth } from '../contexts/BackendHealthContext';

export const BackendOfflineError: React.FC = () => {
  const { checkHealth } = useBackendHealth();

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Error Icon */}
        <div className="mx-auto w-24 h-24 rounded-full bg-destructive/10 flex items-center justify-center">
          <svg
            className="w-12 h-12 text-destructive"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        {/* Error Message */}
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold text-foreground">Backend Server Offline</h2>
          <p className="text-foreground-secondary">
            Unable to connect to the backend server. Please ensure the server is running and try
            again.
          </p>
        </div>

        {/* Error Details */}
        <div className="bg-background-elevated border border-border rounded-lg p-4 text-left space-y-2">
          <h3 className="text-sm font-medium text-foreground">Troubleshooting Steps:</h3>
          <ul className="text-sm text-foreground-secondary space-y-1 list-disc list-inside">
            <li>Check if the backend server is running</li>
            <li>Verify the server URL and port configuration</li>
            <li>Ensure no firewall is blocking the connection</li>
            <li>Check the server logs for any errors</li>
          </ul>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => checkHealth()}
            className={cn(
              'px-4 py-2 rounded-lg font-medium transition-all duration-200',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2'
            )}
          >
            Retry Connection
          </button>
          <button
            onClick={() => window.location.reload()}
            className={cn(
              'px-4 py-2 rounded-lg font-medium transition-all duration-200',
              'bg-background-elevated border border-border text-foreground-secondary',
              'hover:bg-background-tertiary hover:text-foreground',
              'focus:outline-none focus:ring-2 focus:ring-border'
            )}
          >
            Refresh Page
          </button>
        </div>

        {/* Status */}
        <div className="text-xs text-foreground-tertiary">
          <p>Connection attempts are made every 5 seconds</p>
        </div>
      </div>
    </div>
  );
};
