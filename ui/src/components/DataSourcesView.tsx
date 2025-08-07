import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { Button } from './ui/button';
import { Document, Attach, TrashIcon } from './icons';
import Close from './icons/Close';
import YouTube from './icons/YouTube';
import { cn } from '../utils';
import { toast } from 'react-toastify';
import { PhaseProgress } from './PhaseProgress';
import {
  getManualDataSources,
  postManualProcessFileAsync,
  postManualProcessUrlAsync,
  postManualDeleteDataSource,
  postManualDeleteDataSourcesByName,
  postManualIngestionStatus,
  getManualActiveDataSources,
  postManualMarkDataSourcesAsActive,
  postManualMarkDataSourcesAsInactive,
  postManualReprocessFileAsync,
} from '../server-client/sdk.gen';
import type {
  DataSourcesResponse,
  DeleteDataSourceResponse,
  DeleteDataSourcesByNameResponse,
  DataSourceFile,
  IngestionStatusResponse,
  ErrorResponse,
} from '../server-client/types.gen';

type ProcessFileAsyncDataWithName = {
  body: {
    file_path: string;
    source_name?: string;
  };
};

type GroupedDataSource = {
  name: string;
  files: DataSourceFile[];
  totalVectorCount: number;
  totalDimension: number;
  aggregatedStatus:
    | 'not_found'
    | 'processing'
    | 'completed'
    | 'failed'
    | 'partially_successful'
    | 'need_processing';
  processingProgress?: {
    phases?: Array<{
      phase:
        | 'initialization'
        | 'downloading'
        | 'transcription'
        | 'embedding'
        | 'storing'
        | 'completed';
      is_current_phase: boolean;
      percentage: number;
    }>;
  };
};

function groupDataSourcesByName(dataSources: DataSourceFile[]): GroupedDataSource[] {
  const groups = new Map<string, DataSourceFile[]>();

  dataSources.forEach((source) => {
    const name = source.source_name || source.source_path;
    const existingGroup = groups.get(name);
    if (existingGroup) {
      existingGroup.push(source);
    } else {
      groups.set(name, [source]);
    }
  });

  return Array.from(groups.entries()).map(([name, files]) => {
    const sortedFiles = files.sort((a, b) => a.source_path.localeCompare(b.source_path));
    const totalVectorCount = sortedFiles.reduce((sum, file) => sum + file.vector_count, 0);

    let aggregatedStatus:
      | 'not_found'
      | 'processing'
      | 'completed'
      | 'failed'
      | 'partially_successful'
      | 'need_processing';
    if (sortedFiles.some((file) => file.status === 'processing')) {
      aggregatedStatus = 'processing';
    } else if (sortedFiles.every((file) => file.status === 'completed')) {
      aggregatedStatus = 'completed';
    } else if (sortedFiles.some((file) => file.status === 'need_processing')) {
      aggregatedStatus = 'need_processing';
    } else if (
      sortedFiles.some((file) => file.status === 'completed') &&
      sortedFiles.some((file) => file.status === 'failed')
    ) {
      aggregatedStatus = 'partially_successful';
    } else if (sortedFiles.some((file) => file.status === 'failed')) {
      aggregatedStatus = 'failed';
    } else {
      aggregatedStatus = 'not_found';
    }

    const totalDimension = sortedFiles[0]?.dimension || 0;

    return {
      name,
      files: sortedFiles,
      totalVectorCount,
      totalDimension,
      aggregatedStatus,
      processingProgress: undefined,
    };
  });
}

function shortenPath(fullPath: string, maxLength: number = 50): string {
  if (fullPath.length <= maxLength) return fullPath;

  const separator = fullPath.includes('/') ? '/' : '\\';
  const parts = fullPath.split(separator);
  const fileName = parts[parts.length - 1];

  if (fileName.length > maxLength - 10) {
    const ext = fileName.lastIndexOf('.') > 0 ? fileName.slice(fileName.lastIndexOf('.')) : '';
    const nameWithoutExt = fileName.slice(0, fileName.lastIndexOf('.'));
    return '...' + separator + nameWithoutExt.slice(0, maxLength - 13 - ext.length) + '...' + ext;
  }

  const availableSpace = maxLength - fileName.length - 6;

  if (parts.length > 2) {
    const pathStart = parts[0];
    let pathEnd = '';
    let i = parts.length - 2;

    while (i > 0 && pathStart.length + pathEnd.length + parts[i].length + 1 < availableSpace) {
      pathEnd = separator + parts[i] + pathEnd;
      i--;
    }

    if (i > 0) {
      return pathStart + separator + '...' + pathEnd + separator + fileName;
    } else {
      return fullPath;
    }
  }

  return '...' + separator + fileName;
}

interface DataSourcesViewProps {
  isSidebarCollapsed?: boolean;
}

export function DataSourcesView({ isSidebarCollapsed = false }: DataSourcesViewProps) {
  const [dataSources, setDataSources] = useState<DataSourceFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [isAddingFile, setIsAddingFile] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [dataSourceToDelete, setDataSourceToDelete] = useState<DataSourceFile | null>(null);
  const [groupToDelete, setGroupToDelete] = useState<GroupedDataSource | null>(null);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [ingestionProgress, setIngestionProgress] = useState<{
    [key: string]: {
      phases?: Array<{
        phase:
          | 'initialization'
          | 'downloading'
          | 'transcription'
          | 'embedding'
          | 'storing'
          | 'completed';
        is_current_phase: boolean;
        percentage: number;
      }>;
    };
  }>({});
  const [pollIntervals, setPollIntervals] = useState<{ [key: string]: NodeJS.Timeout }>({});
  const [showAddFileModal, setShowAddFileModal] = useState(false);
  const [customFileName, setCustomFileName] = useState('');
  const [inputMode, setInputMode] = useState<'file' | 'url'>('file');
  const [urlInput, setUrlInput] = useState('');
  const [activeDataSources, setActiveDataSources] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const hasShownFetchErrorRef = useRef(false);

  // Update a single data source's status without refetching all
  const updateDataSourceStatus = useCallback(
    async (filePath: string, newStatus: 'completed' | 'failed') => {
      // Update status immediately for responsiveness
      setDataSources((prev) =>
        prev.map((source) =>
          source.source_path === filePath ? { ...source, status: newStatus } : source
        )
      );

      // If completed, fetch just this source's updated data to get vector count
      if (newStatus === 'completed') {
        try {
          const response = await getManualDataSources({ query: { source: filePath } });
          const data = response.data as DataSourcesResponse;

          if (data.status === 'success' && data.files.length > 0) {
            const updatedSource = data.files[0];
            setDataSources((prev) =>
              prev.map((source) =>
                source.source_path === filePath ? { ...source, ...updatedSource } : source
              )
            );
          }
        } catch (err) {
          console.warn('Failed to fetch updated source data:', err);
        }
      }
    },
    []
  );

  const startPollingIngestionStatus = useCallback(
    (filePath: string) => {
      const interval = setInterval(async () => {
        try {
          const response = await postManualIngestionStatus({
            body: { source: filePath },
          });

          const statusData = response.data as IngestionStatusResponse;

          if (
            statusData.status === 'success' &&
            statusData.ingestion_status === 'processing' &&
            statusData.progress?.phase_progresses
          ) {
            setIngestionProgress((prev) => ({
              ...prev,
              [filePath]: {
                phases: statusData.progress!.phase_progresses,
              },
            }));
          } else if (statusData.ingestion_status === 'completed') {
            clearInterval(interval);
            setPollIntervals((prev) => {
              const newIntervals = { ...prev };
              delete newIntervals[filePath];
              return newIntervals;
            });
            setIngestionProgress((prev) => {
              const newProgress = { ...prev };
              delete newProgress[filePath];
              return newProgress;
            });
            // Update just this source's status instead of refetching all
            updateDataSourceStatus(filePath, 'completed').then(() => {
              toast.success(`Processing completed for ${filePath.split('/').pop()}`, {
                autoClose: 1000,
              });
            });
          } else if (statusData.ingestion_status === 'failed') {
            clearInterval(interval);
            setPollIntervals((prev) => {
              const newIntervals = { ...prev };
              delete newIntervals[filePath];
              return newIntervals;
            });
            setIngestionProgress((prev) => {
              const newProgress = { ...prev };
              delete newProgress[filePath];
              return newProgress;
            });
            if (statusData.message) {
              toast.error(`Processing failed: ${statusData.message}`);
            }
            // Update just this source's status instead of refetching all
            updateDataSourceStatus(filePath, 'failed');
          }
        } catch (err) {
          console.warn('Failed to fetch ingestion status for', filePath, err);
        }
      }, 1000);

      setPollIntervals((prev) => ({ ...prev, [filePath]: interval }));
    },
    [updateDataSourceStatus]
  );

  useEffect(() => {
    return () => {
      Object.values(pollIntervals).forEach((interval) => clearInterval(interval));
    };
  }, [pollIntervals]);

  // This useEffect will be moved after fetchDataSources and fetchActiveDataSources are defined

  const fetchActiveDataSources = useCallback(async () => {
    try {
      const response = await getManualActiveDataSources();
      if (
        response.data &&
        'active_data_sources' in response.data &&
        Array.isArray(response.data.active_data_sources)
      ) {
        setActiveDataSources(new Set(response.data.active_data_sources));
      }
    } catch (err) {
      console.warn('Failed to fetch active data sources:', err);
    }
  }, []);

  const fetchDataSources = useCallback(
    async (isRefresh = false) => {
      if (!isRefresh) {
        setLoading(true);
      }

      try {
        const sourcesResponse = await getManualDataSources();

        const sourcesData = sourcesResponse.data as DataSourcesResponse;

        if (sourcesData.status === 'success') {
          // Smart update: only update if data has changed
          setDataSources((prevSources) => {
            // Create a map of existing sources for quick lookup
            const existingMap = new Map(prevSources.map((s) => [s.source_path, s]));

            // Check if anything has actually changed
            const hasChanges =
              sourcesData.files.length !== prevSources.length ||
              sourcesData.files.some((newFile) => {
                const existing = existingMap.get(newFile.source_path);
                return (
                  !existing ||
                  existing.vector_count !== newFile.vector_count ||
                  existing.status !== newFile.status ||
                  existing.dimension !== newFile.dimension ||
                  existing.source_name !== newFile.source_name
                );
              });

            // Only update state if there are actual changes
            if (hasChanges) {
              return sourcesData.files;
            }
            return prevSources;
          });

          hasShownFetchErrorRef.current = false; // Reset error flag on successful fetch

          sourcesData.files.forEach((file) => {
            if (file.status === 'processing' && !pollIntervals[file.source_path]) {
              startPollingIngestionStatus(file.source_path);
            }
          });
        }
      } catch (err) {
        const errorMessage = 'Backend server not available.';

        // Only show toast on initial load or if it's not a refresh
        if (!isRefresh && !hasShownFetchErrorRef.current) {
          toast.error(errorMessage, { autoClose: 5000 });
          hasShownFetchErrorRef.current = true;
        }

        if (!isRefresh) {
          setDataSources([]);
        }
      } finally {
        if (!isRefresh) {
          setLoading(false);
        }
      }
    },
    [pollIntervals] // eslint-disable-line react-hooks/exhaustive-deps
  );

  // Load data sources and start smart refresh interval
  useEffect(() => {
    fetchDataSources();
    fetchActiveDataSources();

    // Periodic refresh that only updates if data has changed
    const refreshInterval = setInterval(() => {
      fetchDataSources(true);
      fetchActiveDataSources();
    }, 5000);

    return () => clearInterval(refreshInterval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAddFile = () => {
    setShowAddFileModal(true);
    setCustomFileName('');
    setUrlInput('');
    setInputMode('file');
  };

  const handleConfirmAddFile = useCallback(async () => {
    try {
      setIsAddingFile(true);

      if (inputMode === 'url') {
        if (!urlInput.trim()) {
          const errorMsg = 'Please enter a URL';
          toast.error(errorMsg, { autoClose: 5000 });
          return;
        }

        const response = await postManualProcessUrlAsync({
          body: {
            url: urlInput.trim(),
            ...(customFileName.trim() && { source_name: customFileName.trim() }),
          },
        });

        // Check if there's an error in the response
        if (response.error) {
          const errorData = response.error as ErrorResponse;
          const errorMsg = errorData?.error || 'Failed to process URL';
          toast.error(errorMsg, { autoClose: 5000 });
          return;
        }

        // If we reach here, the request was successful (201 status)
        await fetchDataSources(true);
        setShowAddFileModal(false);
      } else {
        const filePath = await window.electron.selectFileOrDirectory();

        if (filePath) {
          const requestBody: ProcessFileAsyncDataWithName['body'] = {
            file_path: filePath,
            ...(customFileName.trim() && { source_name: customFileName.trim() }),
          };

          const response = await postManualProcessFileAsync({
            body: requestBody,
          } as ProcessFileAsyncDataWithName);

          // Check if there's an error in the response
          if (response.error) {
            // Handle error response
            const errorData = response.error as ErrorResponse;
            const errorMsg = errorData?.error || 'Failed to process file';
            toast.error(errorMsg, { autoClose: 5000 });
            return;
          }

          // If we reach here, the request was successful (201 status)
          startPollingIngestionStatus(filePath);
          await fetchDataSources(true);
          setShowAddFileModal(false);
        }
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to add data source';
      toast.error(errorMsg, { autoClose: 5000 });
    } finally {
      setIsAddingFile(false);
    }
  }, [inputMode, urlInput, customFileName, fetchDataSources]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCancelAddFile = useCallback(() => {
    setShowAddFileModal(false);
    setCustomFileName('');
    setUrlInput('');
    setInputMode('file');
  }, []);

  // Handle keyboard shortcuts for the add file modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (showAddFileModal) {
        if (e.key === 'Escape') {
          handleCancelAddFile();
        } else if (e.key === 'Enter' && !isAddingFile) {
          handleConfirmAddFile();
        }
      }
    };

    if (showAddFileModal) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [showAddFileModal, isAddingFile, handleCancelAddFile, handleConfirmAddFile]);

  const handleDeleteDataSource = (dataSource: DataSourceFile) => {
    setDataSourceToDelete(dataSource);
    setGroupToDelete(null);
    setShowDeleteConfirmation(true);
  };

  const handleDeleteGroup = (group: GroupedDataSource) => {
    setGroupToDelete(group);
    setDataSourceToDelete(null);
    setShowDeleteConfirmation(true);
  };

  const handleConfirmDelete = async () => {
    if (!dataSourceToDelete && !groupToDelete) return;

    setIsDeleting(true);
    // setError(null);

    try {
      if (groupToDelete) {
        // Handle bulk delete of selected files
        if (selectedFiles.size > 0) {
          // Delete each selected file individually
          const filesToDelete = dataSources.filter((ds) => selectedFiles.has(ds.source_path));
          let deletedCount = 0;

          for (const file of filesToDelete) {
            const response = await postManualDeleteDataSource({
              body: { source: file.source_path },
            });

            const result = response.data as DeleteDataSourceResponse;

            if (result.status === 'success' && result.data_source_was_found) {
              deletedCount++;
              if (pollIntervals[file.source_path]) {
                clearInterval(pollIntervals[file.source_path]);
                setPollIntervals((prev) => {
                  const newIntervals = { ...prev };
                  delete newIntervals[file.source_path];
                  return newIntervals;
                });
                setIngestionProgress((prev) => {
                  const newProgress = { ...prev };
                  delete newProgress[file.source_path];
                  return newProgress;
                });
              }
            }
          }

          // Clear selection after bulk delete
          setSelectedGroups(new Set());
          setSelectedFiles(new Set());
          setIsSelectionMode(false);

          await fetchDataSources(true);
          toast.success(`Deleted ${deletedCount} file${deletedCount !== 1 ? 's' : ''}`, {
            autoClose: 2000,
          });
        } else {
          // Single group delete - check if it's a single file or multi-file group
          if (groupToDelete.files.length === 1) {
            // Single file group - use delete_data_source endpoint
            const response = await postManualDeleteDataSource({
              body: { source: groupToDelete.files[0].source_path },
            });

            const result = response.data as DeleteDataSourceResponse;

            if (result.status === 'success' && result.data_source_was_found) {
              const file = groupToDelete.files[0];
              if (pollIntervals[file.source_path]) {
                clearInterval(pollIntervals[file.source_path]);
                setPollIntervals((prev) => {
                  const newIntervals = { ...prev };
                  delete newIntervals[file.source_path];
                  return newIntervals;
                });
                setIngestionProgress((prev) => {
                  const newProgress = { ...prev };
                  delete newProgress[file.source_path];
                  return newProgress;
                });
              }

              await fetchDataSources(true);
            } else if (!result.data_source_was_found) {
              const errorMsg = `Data source not found: ${groupToDelete.name}`;
              toast.error(errorMsg, { autoClose: 5000 });
            } else {
              const errorMsg = 'Failed to delete data source';
              toast.error(errorMsg, { autoClose: 5000 });
            }
          } else {
            // Multi-file group - use delete_data_sources_by_name endpoint
            const response = await postManualDeleteDataSourcesByName({
              body: { source_name: groupToDelete.name },
            });

            const result = response.data as DeleteDataSourcesByNameResponse;

            if (result.status === 'success') {
              groupToDelete.files.forEach((file) => {
                if (pollIntervals[file.source_path]) {
                  clearInterval(pollIntervals[file.source_path]);
                }
              });

              setPollIntervals((prev) => {
                const newIntervals = { ...prev };
                groupToDelete.files.forEach((file) => {
                  delete newIntervals[file.source_path];
                });
                return newIntervals;
              });

              setIngestionProgress((prev) => {
                const newProgress = { ...prev };
                groupToDelete.files.forEach((file) => {
                  delete newProgress[file.source_path];
                });
                return newProgress;
              });

              await fetchDataSources(true);
            } else {
              const errorMsg = 'Failed to delete data source group';
              toast.error(errorMsg, { autoClose: 5000 });
            }
          }
        }
      } else if (dataSourceToDelete) {
        const response = await postManualDeleteDataSource({
          body: { source: dataSourceToDelete.source_path },
        });

        const result = response.data as DeleteDataSourceResponse;

        if (result.status === 'success') {
          if (result.data_source_was_found) {
            if (pollIntervals[dataSourceToDelete.source_path]) {
              clearInterval(pollIntervals[dataSourceToDelete.source_path]);
              setPollIntervals((prev) => {
                const newIntervals = { ...prev };
                delete newIntervals[dataSourceToDelete.source_path];
                return newIntervals;
              });
              setIngestionProgress((prev) => {
                const newProgress = { ...prev };
                delete newProgress[dataSourceToDelete.source_path];
                return newProgress;
              });
            }

            await fetchDataSources(true);
          } else {
            const errorMsg = `Data source not found: ${dataSourceToDelete.source_name}`;
            // setError(errorMsg);
            toast.error(errorMsg, { autoClose: 5000 });
          }
        } else {
          const errorMsg = 'Failed to delete data source';
          // setError(errorMsg);
          toast.error(errorMsg, { autoClose: 5000 });
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete data source';
      // setError(errorMsg);
      toast.error(errorMsg, { autoClose: 5000 });
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirmation(false);
      setDataSourceToDelete(null);
      setGroupToDelete(null);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirmation(false);
    setDataSourceToDelete(null);
    setGroupToDelete(null);
  };

  const handleToggleDataSourceActive = async (dataSource: DataSourceFile) => {
    try {
      const isActive = activeDataSources.has(dataSource.source_path);
      const endpoint = isActive
        ? postManualMarkDataSourcesAsInactive
        : postManualMarkDataSourcesAsActive;

      const response = await endpoint({
        body: { source_paths: [dataSource.source_path] },
      });

      if (response.data && 'active_data_sources' in response.data) {
        setActiveDataSources(new Set(response.data.active_data_sources));
      }
    } catch (err) {
      const errorMsg = 'Failed to update data source active state';
      // setError(errorMsg);
      toast.error(errorMsg, { autoClose: 5000 });
    }
  };

  const handleToggleGroupActive = async (group: GroupedDataSource) => {
    try {
      const activeFiles = group.files.filter((file) => activeDataSources.has(file.source_path));
      const allActive = activeFiles.length === group.files.length;

      const endpoint = allActive
        ? postManualMarkDataSourcesAsInactive
        : postManualMarkDataSourcesAsActive;
      const sourcePaths = group.files.map((file) => file.source_path);

      const response = await endpoint({
        body: { source_paths: sourcePaths },
      });

      if (response.data && 'active_data_sources' in response.data) {
        setActiveDataSources(new Set(response.data.active_data_sources));
      }
    } catch (err) {
      const errorMsg = 'Failed to update group active state';
      // setError(errorMsg);
      toast.error(errorMsg, { autoClose: 5000 });
    }
  };

  const toggleGroupExpansion = (groupName: string) => {
    setExpandedGroups((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(groupName)) {
        newSet.delete(groupName);
      } else {
        newSet.add(groupName);
      }
      return newSet;
    });
  };

  const toggleGroupSelection = (groupName: string) => {
    const group = groupedSources.find((g) => g.name === groupName);
    if (!group) return;

    setSelectedGroups((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(groupName)) {
        newSet.delete(groupName);
        // Also deselect all files in this group
        setSelectedFiles((prevFiles) => {
          const newFiles = new Set(prevFiles);
          group.files.forEach((file) => {
            newFiles.delete(file.source_path);
          });
          return newFiles;
        });
      } else {
        newSet.add(groupName);
        // Also select all files in this group
        setSelectedFiles((prevFiles) => {
          const newFiles = new Set(prevFiles);
          group.files.forEach((file) => {
            newFiles.add(file.source_path);
          });
          return newFiles;
        });
      }
      // Enter selection mode when selecting items
      if (newSet.size > 0 || selectedFiles.size > 0) {
        setIsSelectionMode(true);
      }
      return newSet;
    });
  };

  const toggleFileSelection = (filePath: string, groupName: string) => {
    const group = groupedSources.find((g) => g.name === groupName);
    if (!group) return;

    setSelectedFiles((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(filePath)) {
        newSet.delete(filePath);

        // Check if we should deselect the group
        const groupFilePaths = group.files.map((f) => f.source_path);
        const hasSelectedFile = groupFilePaths.some((fp) => newSet.has(fp));
        if (!hasSelectedFile) {
          setSelectedGroups((prevGroups) => {
            const newGroups = new Set(prevGroups);
            newGroups.delete(groupName);
            return newGroups;
          });
        }
      } else {
        newSet.add(filePath);

        // Check if we should select the group
        const groupFilePaths = group.files.map((f) => f.source_path);
        const allFilesSelected = groupFilePaths.every((fp) => fp === filePath || newSet.has(fp));
        if (allFilesSelected) {
          setSelectedGroups((prevGroups) => {
            const newGroups = new Set(prevGroups);
            newGroups.add(groupName);
            return newGroups;
          });
        }
      }

      // Enter selection mode when selecting items
      if (newSet.size > 0 || selectedGroups.size > 0) {
        setIsSelectionMode(true);
      }
      return newSet;
    });
  };

  const groupedSources = useMemo(() => {
    const grouped = groupDataSourcesByName(dataSources);

    // Update processing progress
    grouped.forEach((group) => {
      if (group.aggregatedStatus === 'processing') {
        const processingFiles = group.files.filter((file) => file.status === 'processing');

        // Get the progress for the first processing file (assuming all files in a group share the same progress)
        const firstProcessingFile = processingFiles[0];
        if (firstProcessingFile) {
          const progress = ingestionProgress[firstProcessingFile.source_path];
          if (progress) {
            group.processingProgress = progress;
          }
        }
      }
    });

    return grouped;
  }, [dataSources, ingestionProgress]);

  const filteredSources = useMemo(() => {
    return groupedSources.filter((group) => {
      const matchesSearch =
        searchQuery === '' ||
        group.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        group.files.some((file) =>
          file.source_path.toLowerCase().includes(searchQuery.toLowerCase())
        );

      const matchesStatus = selectedStatus === 'all' || group.aggregatedStatus === selectedStatus;

      return matchesSearch && matchesStatus;
    });
  }, [groupedSources, searchQuery, selectedStatus]);

  const selectAllGroups = useCallback(() => {
    const allGroupNames = filteredSources.map((g) => g.name);
    setSelectedGroups(new Set(allGroupNames));
    // Also select all files
    const allFilePaths = filteredSources.flatMap((g) => g.files.map((f) => f.source_path));
    setSelectedFiles(new Set(allFilePaths));
    setIsSelectionMode(true);
  }, [filteredSources]);

  const deselectAllGroups = useCallback(() => {
    setSelectedGroups(new Set());
    setSelectedFiles(new Set());
    setIsSelectionMode(false);
  }, []);

  const handleBulkDelete = () => {
    if (selectedGroups.size === 0 && selectedFiles.size === 0) return;

    // Calculate total files and vectors to delete
    const filesToDelete = dataSources.filter((ds) => selectedFiles.has(ds.source_path));
    const totalVectors = filesToDelete.reduce((sum, f) => sum + f.vector_count, 0);
    const totalFiles = selectedFiles.size;

    setGroupToDelete({
      name: `${totalFiles} ${totalFiles === 1 ? 'file' : 'files'}`,
      files: [],
      totalVectorCount: totalVectors,
      totalDimension: 0,
      aggregatedStatus: 'completed' as const,
      processingProgress: undefined,
    });
    setDataSourceToDelete(null);
    setShowDeleteConfirmation(true);
  };

  const handleBulkReprocess = async () => {
    if (selectedGroups.size === 0 && selectedFiles.size === 0) return;

    setIsReprocessing(true);
    try {
      const filesToReprocess = dataSources.filter((ds) => selectedFiles.has(ds.source_path));
      let totalFilesReprocessed = 0;
      let totalErrors = 0;
      let skippedYouTubeFiles = 0;

      for (const file of filesToReprocess) {
        // Skip YouTube data sources
        if (file.source_path.includes('youtube.com') || file.source_path.includes('youtu.be')) {
          skippedYouTubeFiles++;
          continue;
        }
        try {
          const response = await postManualReprocessFileAsync({
            body: {
              file_path: file.source_path,
              ...(file.source_name && { source_name: file.source_name }),
            },
          });

          // Check if there's an error in the response
          if (response.error) {
            totalErrors++;
          } else if (
            response.data &&
            'status' in response.data &&
            response.data.status === 'success'
          ) {
            totalFilesReprocessed++;
            // Start polling for this file's progress
            startPollingIngestionStatus(file.source_path);
          } else {
            totalErrors++;
          }
        } catch (err: unknown) {
          totalErrors++;
        }
      }

      // Clear selection after reprocessing
      setSelectedGroups(new Set());
      setSelectedFiles(new Set());
      setIsSelectionMode(false);

      // Refresh data sources
      await fetchDataSources(true);

      // Show appropriate toast message
      if (skippedYouTubeFiles > 0 && totalFilesReprocessed === 0 && totalErrors === 0) {
        toast.info(
          `Skipped ${skippedYouTubeFiles} YouTube file${skippedYouTubeFiles > 1 ? 's' : ''} (YouTube sources cannot be reprocessed)`,
          {
            autoClose: 4000,
          }
        );
      } else if (totalFilesReprocessed > 0 && totalErrors === 0 && skippedYouTubeFiles === 0) {
        toast.success(
          `Started reprocessing ${totalFilesReprocessed} file${totalFilesReprocessed > 1 ? 's' : ''}`,
          {
            autoClose: 3000,
          }
        );
      } else if (totalFilesReprocessed > 0 && totalErrors === 0 && skippedYouTubeFiles > 0) {
        toast.success(
          `Started reprocessing ${totalFilesReprocessed} file${totalFilesReprocessed > 1 ? 's' : ''}, skipped ${skippedYouTubeFiles} YouTube file${skippedYouTubeFiles > 1 ? 's' : ''}`,
          {
            autoClose: 4000,
          }
        );
      } else if (totalFilesReprocessed > 0 && totalErrors > 0) {
        toast.warning(
          `Reprocessed ${totalFilesReprocessed} file${totalFilesReprocessed > 1 ? 's' : ''}, ${totalErrors} error${totalErrors > 1 ? 's' : ''}${skippedYouTubeFiles > 0 ? `, skipped ${skippedYouTubeFiles} YouTube file${skippedYouTubeFiles > 1 ? 's' : ''}` : ''}`,
          {
            autoClose: 5000,
          }
        );
      } else if (totalFilesReprocessed === 0 && totalErrors === 0 && skippedYouTubeFiles === 0) {
        toast.error(`Failed to reprocess files`, {
          autoClose: 5000,
        });
      }
    } catch (err) {
      toast.error('Failed to reprocess selected files', {
        autoClose: 5000,
      });
    } finally {
      setIsReprocessing(false);
    }
  };

  // Handle keyboard shortcuts for selection
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+A or Ctrl+A for select all
      if ((e.metaKey || e.ctrlKey) && e.key === 'a' && filteredSources.length > 0) {
        e.preventDefault();
        if (selectedGroups.size === filteredSources.length) {
          deselectAllGroups();
        } else {
          selectAllGroups();
        }
      }
      // Escape to cancel selection
      if (e.key === 'Escape' && (selectedGroups.size > 0 || selectedFiles.size > 0)) {
        deselectAllGroups();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [
    filteredSources,
    selectedGroups.size,
    selectedFiles.size,
    selectAllGroups,
    deselectAllGroups,
  ]);

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center h-full')}>
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-foreground-secondary">Loading data sources...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('min-h-screen transition-all duration-300', isSidebarCollapsed && 'pl-16')}>
      <div
        className={cn(
          'max-w-7xl mx-auto px-6 py-8 transition-all duration-300',
          (selectedGroups.size > 0 || selectedFiles.size > 0) && 'pb-28'
        )}
      >
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight mb-2">Data Sources</h1>
          <p className="text-foreground-secondary">Manage your vector databases and embeddings</p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-background border border-border rounded-xl p-4">
            <p className="text-sm text-foreground-secondary mb-1">Total Sources</p>
            <p className="text-2xl font-semibold">{groupedSources.length}</p>
          </div>
          <div className="bg-background border border-border rounded-xl p-4">
            <p className="text-sm text-foreground-secondary mb-1">Total Vectors</p>
            <p className="text-2xl font-semibold">
              {dataSources.reduce((sum, ds) => sum + ds.vector_count, 0).toLocaleString()}
            </p>
          </div>
          <div className="bg-background border border-border rounded-xl p-4">
            <p className="text-sm text-foreground-secondary mb-1">Active Sources</p>
            <p className="text-2xl font-semibold text-accent-success">
              {
                groupedSources.filter((g) =>
                  g.files.some((f) => activeDataSources.has(f.source_path))
                ).length
              }
            </p>
          </div>
          <div className="bg-background border border-border rounded-xl p-4">
            <p className="text-sm text-foreground-secondary mb-1">Processing/Partial</p>
            <p className="text-2xl font-semibold text-warning">
              {
                groupedSources.filter(
                  (g) =>
                    g.aggregatedStatus === 'processing' ||
                    g.aggregatedStatus === 'partially_successful' ||
                    g.aggregatedStatus === 'need_processing'
                ).length
              }
            </p>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="flex-1">
            <div className="relative">
              <input
                type="text"
                placeholder="Search data sources..."
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

          <div className="flex items-center gap-2">
            {filteredSources.length > 0 && (
              <Button
                onClick={() => {
                  if (selectedGroups.size === filteredSources.length) {
                    deselectAllGroups();
                  } else {
                    selectAllGroups();
                  }
                }}
                variant="outline"
                size="sm"
                className="h-8"
              >
                <div className="flex items-center gap-1.5">
                  <div
                    className={cn(
                      'w-4 h-4 border rounded transition-all duration-200',
                      selectedGroups.size === filteredSources.length
                        ? 'bg-primary border-primary'
                        : selectedGroups.size > 0
                          ? 'bg-primary/50 border-primary'
                          : 'border-border-strong'
                    )}
                  >
                    {selectedGroups.size > 0 && (
                      <svg className="w-full h-full text-white" viewBox="0 0 24 24" fill="none">
                        <path
                          d="M20 6L9 17L4 12"
                          stroke="currentColor"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                  <span className="text-xs font-medium">
                    {selectedGroups.size === 0
                      ? 'Select All'
                      : selectedGroups.size === filteredSources.length
                        ? 'Deselect All'
                        : `${selectedGroups.size} selected`}
                  </span>
                </div>
              </Button>
            )}

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className={cn(
                'h-8 pl-3 pr-8 bg-background border border-border rounded-lg',
                'text-sm font-medium cursor-pointer appearance-none',
                'hover:bg-background-elevated hover:border-border-strong',
                'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                'transition-all duration-200',
                'bg-[url("data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2012%2012%22%3E%3Cpath%20fill%3D%22%23666%22%20d%3D%22M10.293%203.293%206%207.586%201.707%203.293A1%201%200%200%200%20.293%204.707l5%205a1%201%200%200%200%201.414%200l5-5a1%201%200%201%200-1.414-1.414z%22%2F%3E%3C%2Fsvg%3E")] bg-[length:12px_12px] bg-[right_0.5rem_center] bg-no-repeat'
              )}
            >
              <option value="all">All statuses</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
              <option value="partially_successful">Partial</option>
              <option value="need_processing">Need Processing</option>
            </select>

            <Button
              onClick={handleAddFile}
              disabled={isAddingFile}
              variant="default"
              size="default"
            >
              <Attach className="w-4 h-4" />
              Add Source
            </Button>
          </div>
        </div>

        {/* Data Sources List */}
        <div className="bg-background border border-border rounded-xl overflow-hidden">
          {filteredSources.length > 0 ? (
            <div className="divide-y divide-border">
              {filteredSources.map((group) => {
                const hasMultipleFiles = group.files.length > 1;
                const isExpanded = expandedGroups.has(group.name);
                const isHovered = hoveredRow === group.name;
                const isGroupActive = group.files.some((f) => activeDataSources.has(f.source_path));
                const groupFilePaths = group.files.map((f) => f.source_path);
                const selectedFilesInGroup = groupFilePaths.filter((fp) => selectedFiles.has(fp));
                const isPartiallySelected =
                  selectedFilesInGroup.length > 0 &&
                  selectedFilesInGroup.length < group.files.length;

                return (
                  <div key={group.name}>
                    <div
                      className={cn(
                        'transition-all duration-200',
                        isHovered && 'bg-background-elevated',
                        hasMultipleFiles && 'cursor-pointer',
                        selectedGroups.has(group.name) && 'bg-primary/5'
                      )}
                      onMouseEnter={() => setHoveredRow(group.name)}
                      onMouseLeave={() => setHoveredRow(null)}
                      onClick={() => {
                        if (hasMultipleFiles) {
                          toggleGroupExpansion(group.name);
                        }
                      }}
                    >
                      <div className="px-6 py-4">
                        <div className="flex items-center gap-4">
                          {/* Icon with integrated expansion state */}
                          <div className="relative group/icon">
                            <div
                              className={cn(
                                'w-12 h-12 bg-background-elevated rounded-xl flex items-center justify-center border shadow-sm transition-all duration-200',
                                hasMultipleFiles &&
                                  'cursor-pointer hover:shadow-md hover:scale-105',
                                hasMultipleFiles && isExpanded && 'bg-primary/10 border-primary/30'
                              )}
                            >
                              {group.files.every(
                                (file) =>
                                  file.source_path.includes('youtube.com') ||
                                  file.source_path.includes('youtu.be')
                              ) ? (
                                <YouTube className="w-6 h-6 text-destructive" />
                              ) : (
                                <Document className="w-6 h-6 text-accent-cool" />
                              )}
                            </div>
                            {hasMultipleFiles && (
                              <>
                                <div className="absolute -top-1 -right-1 w-5 h-5 bg-primary rounded-full flex items-center justify-center shadow-sm">
                                  <span className="text-[10px] font-semibold text-white">
                                    {group.files.length}
                                  </span>
                                </div>
                                <div
                                  className={cn(
                                    'absolute -bottom-1 left-1/2 transform -translate-x-1/2 transition-all duration-200',
                                    isExpanded
                                      ? 'opacity-100'
                                      : 'opacity-0 group-hover/icon:opacity-100'
                                  )}
                                >
                                  <svg
                                    className={cn(
                                      'w-3 h-3 text-foreground-tertiary transition-transform duration-200',
                                      isExpanded && 'rotate-180'
                                    )}
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={3}
                                      d="M19 9l-7 7-7-7"
                                    />
                                  </svg>
                                </div>
                              </>
                            )}
                          </div>

                          {/* Name and Path */}
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-foreground">{group.name}</h3>
                            {!hasMultipleFiles && (
                              <p className="text-sm text-foreground-tertiary font-mono mt-0.5">
                                {shortenPath(group.files[0].source_path, 80)}
                              </p>
                            )}
                          </div>

                          {/* Stats */}
                          <div className="flex items-center gap-6 text-sm">
                            <div className="min-w-[80px]">
                              <p className="text-foreground-secondary">Vectors</p>
                              <p className="font-mono font-medium">
                                {group.totalVectorCount.toLocaleString()}
                              </p>
                            </div>
                            <div className="min-w-[90px]">
                              <p className="text-foreground-secondary">Status</p>
                              <p
                                className={cn(
                                  'font-medium capitalize',
                                  group.aggregatedStatus === 'completed' && 'text-accent-success',
                                  group.aggregatedStatus === 'processing' && 'text-warning',
                                  group.aggregatedStatus === 'failed' && 'text-destructive',
                                  group.aggregatedStatus === 'partially_successful' &&
                                    'text-warning',
                                  group.aggregatedStatus === 'need_processing' && 'text-warning'
                                )}
                              >
                                {group.aggregatedStatus === 'partially_successful'
                                  ? 'Partial'
                                  : group.aggregatedStatus === 'need_processing'
                                    ? 'Need Processing'
                                    : group.aggregatedStatus}
                              </p>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-3">
                            {/* Checkbox for selection */}
                            <label
                              className="relative inline-flex items-center cursor-pointer"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                className="sr-only peer"
                                checked={selectedGroups.has(group.name)}
                                onChange={(e) => {
                                  e.stopPropagation();
                                  toggleGroupSelection(group.name);
                                }}
                              />
                              <div
                                className={cn(
                                  'w-5 h-5 border-2 rounded transition-all duration-200',
                                  'hover:border-primary/50',
                                  selectedGroups.has(group.name) || isPartiallySelected
                                    ? 'bg-primary border-primary'
                                    : 'bg-background border-border-strong'
                                )}
                              >
                                {(selectedGroups.has(group.name) || isPartiallySelected) && (
                                  <svg
                                    className="w-full h-full text-white p-0.5"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                  >
                                    {isPartiallySelected && !selectedGroups.has(group.name) ? (
                                      // Minus sign for indeterminate state
                                      <path
                                        d="M5 12h14"
                                        stroke="currentColor"
                                        strokeWidth="3"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                      />
                                    ) : (
                                      // Check mark for fully selected
                                      <path
                                        d="M20 6L9 17L4 12"
                                        stroke="currentColor"
                                        strokeWidth="3"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                      />
                                    )}
                                  </svg>
                                )}
                              </div>
                            </label>

                            {/* Toggle active/inactive */}
                            <label
                              className={cn(
                                'relative inline-flex items-center cursor-pointer transition-opacity duration-200',
                                isSelectionMode && 'opacity-0 pointer-events-none'
                              )}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                className="sr-only peer"
                                checked={isGroupActive}
                                onChange={(e) => {
                                  e.stopPropagation();
                                  hasMultipleFiles
                                    ? handleToggleGroupActive(group)
                                    : handleToggleDataSourceActive(group.files[0]);
                                }}
                              />
                              <div className="w-10 h-5 bg-background-tertiary peer-checked:bg-primary rounded-full peer transition-colors duration-200">
                                <div className="absolute top-0.5 left-[2px] bg-white w-4 h-4 rounded-full transition-transform duration-200 peer-checked:translate-x-5 shadow-sm" />
                              </div>
                            </label>

                            {/* Delete button (only visible on hover when not in selection mode) */}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                hasMultipleFiles
                                  ? handleDeleteGroup(group)
                                  : handleDeleteDataSource(group.files[0]);
                              }}
                              className={cn(
                                'transition-all duration-200',
                                isSelectionMode
                                  ? 'opacity-0 pointer-events-none'
                                  : isHovered
                                    ? 'opacity-100'
                                    : 'opacity-0'
                              )}
                            >
                              <TrashIcon className="w-4 h-4 text-destructive" />
                            </Button>
                          </div>
                        </div>

                        {/* Progress bar for processing */}
                        {group.aggregatedStatus === 'processing' &&
                          group.processingProgress?.phases && (
                            <div className="mt-3 ml-16 mr-4">
                              <PhaseProgress
                                phases={group.processingProgress.phases}
                                isCompact={!isExpanded && !isHovered}
                              />
                            </div>
                          )}
                      </div>
                    </div>

                    {/* Expanded Files */}
                    {hasMultipleFiles && isExpanded && (
                      <div className="bg-background-elevated border-t border-border">
                        {group.files.map((file, index) => (
                          <div
                            key={file.source_path}
                            className={cn(
                              'px-6 py-3 flex items-center gap-4',
                              index !== group.files.length - 1 && 'border-b border-border',
                              selectedFiles.has(file.source_path) && 'bg-primary/5'
                            )}
                          >
                            <div className="w-12" />
                            {/* Checkbox for individual file selection */}
                            <label
                              className="relative inline-flex items-center cursor-pointer"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                className="sr-only peer"
                                checked={selectedFiles.has(file.source_path)}
                                onChange={(e) => {
                                  e.stopPropagation();
                                  toggleFileSelection(file.source_path, group.name);
                                }}
                              />
                              <div
                                className={cn(
                                  'w-5 h-5 border-2 rounded transition-all duration-200',
                                  'hover:border-primary/50',
                                  selectedFiles.has(file.source_path)
                                    ? 'bg-primary border-primary'
                                    : 'bg-background border-border-strong'
                                )}
                              >
                                {selectedFiles.has(file.source_path) && (
                                  <svg
                                    className="w-full h-full text-white p-0.5"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                  >
                                    <path
                                      d="M20 6L9 17L4 12"
                                      stroke="currentColor"
                                      strokeWidth="3"
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                    />
                                  </svg>
                                )}
                              </div>
                            </label>
                            <div className="w-10 h-10 bg-background rounded-lg flex items-center justify-center border border-border/50">
                              <Document className="w-5 h-5 text-foreground-tertiary" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-mono text-foreground-secondary">
                                {shortenPath(file.source_path, 100)}
                              </p>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-foreground-secondary">
                              <span>{file.vector_count.toLocaleString()} vectors</span>
                              <span
                                className={cn(
                                  'capitalize',
                                  file.status === 'completed' && 'text-accent-success',
                                  file.status === 'processing' && 'text-warning',
                                  file.status === 'failed' && 'text-destructive',
                                  file.status === 'need_processing' && 'text-warning'
                                )}
                              >
                                {file.status === 'need_processing'
                                  ? 'Need Processing'
                                  : file.status}
                              </span>
                            </div>
                            {/* Show progress for individual file if processing */}
                            {file.status === 'processing' &&
                              ingestionProgress[file.source_path]?.phases && (
                                <div className="w-48">
                                  <PhaseProgress
                                    phases={ingestionProgress[file.source_path].phases!}
                                    isCompact={true}
                                  />
                                </div>
                              )}
                            <label
                              className={cn(
                                'relative inline-flex items-center cursor-pointer transition-opacity duration-200',
                                isSelectionMode && 'opacity-0 pointer-events-none'
                              )}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                className="sr-only peer"
                                checked={activeDataSources.has(file.source_path)}
                                onChange={() => handleToggleDataSourceActive(file)}
                              />
                              <div className="w-8 h-4 bg-background-tertiary peer-checked:bg-primary rounded-full peer transition-colors duration-200">
                                <div className="absolute top-0.5 left-[2px] bg-white w-3 h-3 rounded-full transition-transform duration-200 peer-checked:translate-x-4 shadow-sm" />
                              </div>
                            </label>
                            <Button
                              variant="ghost"
                              size="icon"
                              className={cn(
                                'h-8 w-8 transition-all duration-200',
                                isSelectionMode && 'opacity-0 pointer-events-none'
                              )}
                              onClick={() => handleDeleteDataSource(file)}
                            >
                              <TrashIcon className="w-3.5 h-3.5 text-destructive" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="px-6 py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Document className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">No data sources found</h3>
              <p className="text-sm text-foreground-secondary mb-4">
                {searchQuery || selectedStatus !== 'all'
                  ? 'Try adjusting your filters'
                  : 'Add your first source to begin using RAG'}
              </p>
              {!searchQuery && selectedStatus === 'all' && (
                <Button onClick={handleAddFile} variant="default">
                  <Attach className="w-4 h-4" />
                  Add First Source
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Add File Modal */}
      {showAddFileModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-background border border-border rounded-xl max-w-md w-full mx-4 p-6 shadow-xl">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Add Data Source</h3>
                <Button
                  onClick={handleCancelAddFile}
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                >
                  <Close className="w-4 h-4" />
                </Button>
              </div>

              <div className="flex gap-2 p-1 bg-background-elevated rounded-lg">
                <button
                  onClick={() => setInputMode('file')}
                  className={cn(
                    'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all',
                    inputMode === 'file'
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-foreground-secondary hover:text-foreground'
                  )}
                >
                  File/Directory
                </button>
                <button
                  onClick={() => setInputMode('url')}
                  className={cn(
                    'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all',
                    inputMode === 'url'
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-foreground-secondary hover:text-foreground'
                  )}
                >
                  YouTube URL
                </button>
              </div>

              {inputMode === 'url' && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">YouTube URL</label>
                  <input
                    type="url"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className={cn(
                      'w-full px-3 py-2 bg-background border border-border rounded-lg',
                      'text-sm placeholder-foreground-tertiary',
                      'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                      'transition-all duration-200'
                    )}
                    autoFocus
                  />
                  <p className="text-xs text-foreground-tertiary">
                    The video will be transcribed and indexed
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium">Custom Name (Optional)</label>
                <input
                  type="text"
                  value={customFileName}
                  onChange={(e) => setCustomFileName(e.target.value)}
                  placeholder="Enter a custom name..."
                  className={cn(
                    'w-full px-3 py-2 bg-background border border-border rounded-lg',
                    'text-sm placeholder-foreground-tertiary',
                    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                    'transition-all duration-200'
                  )}
                  autoFocus={inputMode === 'file'}
                />
                <p className="text-xs text-foreground-tertiary">
                  Leave empty to use the {inputMode === 'url' ? 'video title' : 'filename'}
                </p>
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={handleCancelAddFile}
                  variant="outline"
                  className="flex-1"
                  disabled={isAddingFile}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleConfirmAddFile}
                  variant="default"
                  className="flex-1"
                  disabled={isAddingFile}
                >
                  {isAddingFile ? 'Processing...' : inputMode === 'url' ? 'Add URL' : 'Select File'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirmation && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-background border border-border rounded-xl max-w-md w-full mx-4 p-6 shadow-xl">
            <div className="space-y-6">
              <div className="text-center">
                <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-destructive/10 flex items-center justify-center">
                  <TrashIcon className="w-6 h-6 text-destructive" />
                </div>
                <h3 className="text-lg font-semibold">Delete Data Source</h3>
                <p className="text-sm text-foreground-secondary mt-2">
                  This action cannot be undone. All embeddings and data will be permanently deleted.
                </p>
              </div>

              <div className="bg-background-elevated rounded-lg p-4">
                {groupToDelete ? (
                  <div>
                    <p className="font-medium">{groupToDelete.name}</p>
                    <p className="text-sm text-foreground-secondary mt-1">
                      {groupToDelete.files.length} files •{' '}
                      {groupToDelete.totalVectorCount.toLocaleString()} vectors
                    </p>
                  </div>
                ) : dataSourceToDelete ? (
                  <div>
                    <p className="font-medium">
                      {dataSourceToDelete.source_name ||
                        shortenPath(dataSourceToDelete.source_path)}
                    </p>
                    <p className="text-sm text-foreground-secondary mt-1">
                      {dataSourceToDelete.vector_count.toLocaleString()} vectors
                    </p>
                  </div>
                ) : null}
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={handleCancelDelete}
                  variant="outline"
                  className="flex-1"
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleConfirmDelete}
                  variant="destructive"
                  className="flex-1"
                  disabled={isDeleting}
                >
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Actions Toolbar - Apple Style */}
      <div
        className={cn(
          'fixed bottom-0 left-0 right-0 z-40 transition-all duration-300 ease-out',
          selectedGroups.size > 0 || selectedFiles.size > 0 ? 'translate-y-0' : 'translate-y-full'
        )}
      >
        <div className="bg-background/95 backdrop-blur-xl border-t border-border shadow-[0_-8px_24px_rgba(0,0,0,0.12)] dark:shadow-[0_-8px_24px_rgba(0,0,0,0.4)]">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-foreground">
                  {selectedFiles.size} {selectedFiles.size === 1 ? 'file' : 'files'} selected
                </span>
                <span className="text-sm text-foreground-secondary">
                  (
                  {dataSources
                    .filter((ds) => selectedFiles.has(ds.source_path))
                    .reduce((sum, ds) => sum + ds.vector_count, 0)
                    .toLocaleString()}{' '}
                  vectors)
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={deselectAllGroups}
                  className="text-foreground-secondary hover:text-foreground"
                >
                  Cancel
                </Button>

                <div className="w-px h-6 bg-border mx-2" />

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkReprocess}
                  disabled={isReprocessing}
                  className="text-foreground"
                >
                  <svg
                    className={cn('w-4 h-4 mr-1.5', isReprocessing && 'animate-spin')}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  {isReprocessing ? 'Reprocessing...' : 'Reprocess'}
                </Button>

                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleBulkDelete}
                  className="bg-red-600 hover:bg-red-700 text-white dark:bg-red-500 dark:hover:bg-red-600"
                >
                  <TrashIcon className="w-4 h-4 mr-1.5" />
                  Delete {selectedFiles.size === 1 ? 'File' : `${selectedFiles.size} Files`}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
