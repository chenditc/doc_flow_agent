/**
 * Global application context and state management
 */

import React, { createContext, useContext, useReducer, useCallback } from 'react';
import type { ReactNode } from 'react';

// State interface
export interface AppState {
  // UI State
  theme: 'light' | 'dark';
  isLoading: boolean;
  error: string | null;
  
  // User preferences
  preferences: {
    autoRefresh: boolean;
    refreshInterval: number;
    defaultView: 'timeline' | 'table';
    showAdvancedDetails: boolean;
  };
}

// Action types
export type AppAction =
  | { type: 'SET_THEME'; payload: 'light' | 'dark' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'UPDATE_PREFERENCES'; payload: Partial<AppState['preferences']> }
  | { type: 'RESET_STATE' };

// Initial state
const initialState: AppState = {
  theme: 'light',
  isLoading: false,
  error: null,
  preferences: {
    autoRefresh: false,
    refreshInterval: 5000,
    defaultView: 'timeline',
    showAdvancedDetails: false,
  },
};

// Reducer function
const appReducer = (state: AppState, action: AppAction): AppState => {
  switch (action.type) {
    case 'SET_THEME':
      return {
        ...state,
        theme: action.payload,
      };
    
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
    
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
    
    case 'UPDATE_PREFERENCES':
      return {
        ...state,
        preferences: {
          ...state.preferences,
          ...action.payload,
        },
      };
    
    case 'RESET_STATE':
      return initialState;
    
    default:
      return state;
  }
};

// Context interface
interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  
  // Action creators
  setTheme: (theme: 'light' | 'dark') => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  updatePreferences: (preferences: Partial<AppState['preferences']>) => void;
  resetState: () => void;
  clearError: () => void;
}

// Create context
const AppContext = createContext<AppContextType | undefined>(undefined);

// Context provider props
interface AppContextProviderProps {
  children: ReactNode;
  initialState?: Partial<AppState>;
}

// Context provider component
export const AppContextProvider: React.FC<AppContextProviderProps> = ({
  children,
  initialState: initialStateOverride,
}) => {
  const [state, dispatch] = useReducer(
    appReducer,
    { ...initialState, ...initialStateOverride }
  );

  // Action creators
  const setTheme = useCallback((theme: 'light' | 'dark') => {
    dispatch({ type: 'SET_THEME', payload: theme });
  }, []);

  const setLoading = useCallback((isLoading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: isLoading });
  }, []);

  const setError = useCallback((error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  }, []);

  const updatePreferences = useCallback((preferences: Partial<AppState['preferences']>) => {
    dispatch({ type: 'UPDATE_PREFERENCES', payload: preferences });
  }, []);

  const resetState = useCallback(() => {
    dispatch({ type: 'RESET_STATE' });
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: 'SET_ERROR', payload: null });
  }, []);

  const contextValue: AppContextType = {
    state,
    dispatch,
    setTheme,
    setLoading,
    setError,
    updatePreferences,
    resetState,
    clearError,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

// Custom hook to use app context
export const useAppContext = (): AppContextType => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppContextProvider');
  }
  return context;
};

// Export context for testing purposes
export { AppContext };
