import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getManualHealth } from '../server-client';

interface BackendHealthContextType {
  isBackendHealthy: boolean;
  lastCheckTime: Date | null;
  checkHealth: () => Promise<void>;
}

const BackendHealthContext = createContext<BackendHealthContextType | undefined>(undefined);

export const useBackendHealth = () => {
  const context = useContext(BackendHealthContext);
  if (!context) {
    throw new Error('useBackendHealth must be used within BackendHealthProvider');
  }
  return context;
};

interface BackendHealthProviderProps {
  children: React.ReactNode;
  checkInterval?: number; // in milliseconds, default 5 seconds
}

export const BackendHealthProvider: React.FC<BackendHealthProviderProps> = ({
  children,
  checkInterval = 5000,
}) => {
  const [isBackendHealthy, setIsBackendHealthy] = useState(true);
  const [lastCheckTime, setLastCheckTime] = useState<Date | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const response = await getManualHealth();

      // If we get a response, backend is healthy
      if (response.data) {
        setIsBackendHealthy(true);
      } else {
        setIsBackendHealthy(false);
      }
    } catch (error) {
      // If request fails, backend is unhealthy
      console.error('Backend health check failed:', error);
      setIsBackendHealthy(false);
    }

    setLastCheckTime(new Date());
  }, []);

  // Initial health check
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Periodic health checks
  useEffect(() => {
    const interval = setInterval(checkHealth, checkInterval);

    return () => clearInterval(interval);
  }, [checkHealth, checkInterval]);

  // Also check health when window gains focus
  useEffect(() => {
    const handleFocus = () => {
      checkHealth();
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [checkHealth]);

  return (
    <BackendHealthContext.Provider value={{ isBackendHealthy, lastCheckTime, checkHealth }}>
      {children}
    </BackendHealthContext.Provider>
  );
};
