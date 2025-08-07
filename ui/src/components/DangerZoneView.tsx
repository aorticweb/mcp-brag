import React, { useState } from 'react';
import { Button } from './ui/button';
import { TrashIcon } from './icons';
import { toast } from 'react-toastify';
import { postManualDeleteVectors } from '../server-client/sdk.gen';

interface DangerZoneViewProps {
  isSidebarCollapsed?: boolean;
}

export const DangerZoneView: React.FC<DangerZoneViewProps> = () => {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

  const handleClearVectors = async () => {
    setIsClearing(true);
    try {
      const response = await postManualDeleteVectors();
      toast.success(response.message || 'Vector database cleared successfully');
      setShowConfirmDialog(false);
    } catch (error) {
      console.error('Failed to clear vectors:', error);
      toast.error('Failed to clear vector database');
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-8 py-6 border-b border-border/50">
        <h1 className="text-2xl font-semibold text-foreground">Danger Zone</h1>
        <p className="text-foreground-secondary mt-1">
          Destructive actions that can affect your data
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 px-8 py-6">
        <div className="max-w-4xl">
          {/* Clear Vector Database Section */}
          <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-destructive/10 rounded-lg">
                <TrashIcon className="w-6 h-6 text-destructive" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Clear Vector Database
                </h3>
                <p className="text-foreground-secondary mb-4">
                  This will delete all vectors from the database and mark all data sources as
                  needing reprocessing. This action cannot be undone.
                </p>
                <Button
                  variant="destructive"
                  onClick={() => setShowConfirmDialog(true)}
                  disabled={isClearing}
                >
                  Clear Vector Database
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => !isClearing && setShowConfirmDialog(false)}
          />

          {/* Dialog */}
          <div className="relative bg-background border border-border rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-foreground mb-2">Clear Vector Database?</h3>
            <p className="text-foreground-secondary mb-6">
              This will permanently delete all vectors and mark all data sources for reprocessing.
              This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="ghost"
                onClick={() => setShowConfirmDialog(false)}
                disabled={isClearing}
              >
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleClearVectors} disabled={isClearing}>
                {isClearing ? 'Clearing...' : 'Clear Database'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
