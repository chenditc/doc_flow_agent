/**
 * Custom hook for managing localStorage with type safety and React integration
 */

import { useState, useEffect, useCallback } from 'react';

export interface UseLocalStorageOptions<T> {
  serializer?: {
    serialize: (value: T) => string;
    deserialize: (value: string) => T;
  };
  syncAcrossTabs?: boolean;
  onError?: (error: Error) => void;
}

/**
 * Hook for managing localStorage with automatic serialization and React state sync
 */
export const useLocalStorage = <T>(
  key: string,
  initialValue: T,
  options: UseLocalStorageOptions<T> = {}
) => {
  const {
    serializer = {
      serialize: JSON.stringify,
      deserialize: JSON.parse,
    },
    syncAcrossTabs = true,
    onError,
  } = options;

  // Get initial value from localStorage or use provided initial value
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      if (typeof window === 'undefined') {
        return initialValue;
      }

      const item = window.localStorage.getItem(key);
      if (item === null) {
        return initialValue;
      }

      return serializer.deserialize(item);
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      if (onError) {
        onError(error as Error);
      }
      return initialValue;
    }
  });

  // Update localStorage when state changes
  const setValue = useCallback((value: T | ((prevValue: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);

      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, serializer.serialize(valueToStore));
      }
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [key, serializer, storedValue, onError]);

  // Remove item from localStorage
  const removeValue = useCallback(() => {
    try {
      setStoredValue(initialValue);
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(key);
      }
    } catch (error) {
      console.warn(`Error removing localStorage key "${key}":`, error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [key, initialValue, onError]);

  // Listen for storage events to sync across tabs
  useEffect(() => {
    if (!syncAcrossTabs || typeof window === 'undefined') {
      return;
    }

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === key && event.newValue !== null) {
        try {
          const newValue = serializer.deserialize(event.newValue);
          setStoredValue(newValue);
        } catch (error) {
          console.warn(`Error parsing storage event for key "${key}":`, error);
          if (onError) {
            onError(error as Error);
          }
        }
      } else if (event.key === key && event.newValue === null) {
        // Item was removed in another tab
        setStoredValue(initialValue);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [key, serializer, initialValue, syncAcrossTabs, onError]);

  return [storedValue, setValue, removeValue] as const;
};

/**
 * Hook for managing user preferences in localStorage
 */
export const useUserPreferences = () => {
  interface UserPreferences {
    theme: 'light' | 'dark';
    autoRefresh: boolean;
    refreshInterval: number;
    defaultView: 'timeline' | 'table';
    showAdvancedDetails: boolean;
    realtimeEnabled: boolean;
    selectedTraceId: string | null;
    expandedPhases: string[];
    expandedLLMCalls: string[];
  }

  const defaultPreferences: UserPreferences = {
    theme: 'light',
    autoRefresh: false,
    refreshInterval: 5000,
    defaultView: 'timeline',
    showAdvancedDetails: false,
    realtimeEnabled: false,
    selectedTraceId: null,
    expandedPhases: [],
    expandedLLMCalls: [],
  };

  const [preferences, setPreferences, removePreferences] = useLocalStorage(
    'doc-flow-trace-viewer-preferences',
    defaultPreferences,
    {
      syncAcrossTabs: true,
      onError: (error) => {
        console.warn('Error with user preferences:', error);
      },
    }
  );

  const updatePreference = useCallback(<K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    setPreferences(prev => ({
      ...prev,
      [key]: value,
    }));
  }, [setPreferences]);

  const resetPreferences = useCallback(() => {
    setPreferences(defaultPreferences);
  }, [setPreferences, defaultPreferences]);

  return {
    preferences,
    updatePreference,
    resetPreferences,
    removePreferences,
  };
};

/**
 * Hook for managing session data (non-persistent)
 */
export const useSessionStorage = <T>(
  key: string,
  initialValue: T,
  options: UseLocalStorageOptions<T> = {}
) => {
  const {
    serializer = {
      serialize: JSON.stringify,
      deserialize: JSON.parse,
    },
    onError,
  } = options;

  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      if (typeof window === 'undefined') {
        return initialValue;
      }

      const item = window.sessionStorage.getItem(key);
      if (item === null) {
        return initialValue;
      }

      return serializer.deserialize(item);
    } catch (error) {
      console.warn(`Error reading sessionStorage key "${key}":`, error);
      if (onError) {
        onError(error as Error);
      }
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((prevValue: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);

      if (typeof window !== 'undefined') {
        window.sessionStorage.setItem(key, serializer.serialize(valueToStore));
      }
    } catch (error) {
      console.warn(`Error setting sessionStorage key "${key}":`, error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [key, serializer, storedValue, onError]);

  const removeValue = useCallback(() => {
    try {
      setStoredValue(initialValue);
      if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem(key);
      }
    } catch (error) {
      console.warn(`Error removing sessionStorage key "${key}":`, error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [key, initialValue, onError]);

  return [storedValue, setValue, removeValue] as const;
};
