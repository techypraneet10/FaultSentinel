import { useState, useEffect, useCallback } from 'react';
import { ConnectionState, HealthReadyResponse } from '../types';
import { apiService } from '../services/api';

export function useHealth(pollIntervalMs = 30000) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('checking');
  const [readyDetails, setReadyDetails] = useState<HealthReadyResponse | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      // First check liveness
      await apiService.healthLive();
      // Then check readiness
      const ready = await apiService.healthReady();
      setReadyDetails(ready);

      if (ready.status === 'ready') {
        setConnectionState('connected');
      } else {
        setConnectionState('degraded');
      }
    } catch {
      setConnectionState('offline');
      setReadyDetails(null);
    } finally {
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    checkHealth();
    if (pollIntervalMs > 0) {
      const interval = setInterval(checkHealth, pollIntervalMs);
      return () => clearInterval(interval);
    }
  }, [checkHealth, pollIntervalMs]);

  return { connectionState, readyDetails, lastChecked, checkHealth };
}
