/**
 * Trace-specific context and state management
 * Handles trace data, selection, and real-time monitoring
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect, useMemo } from 'react';
import type { ReactNode } from 'react';
import type { TraceSession } from '../types';
import { RealtimeService, createRealtimeService } from '../services/realtimeService';

// State interface
export interface TraceState {
  // Trace data
  availableTraces: string[];
  selectedTraceId: string | null;
  currentTrace: TraceSession | null;
  
  // Real-time monitoring
  isRealTimeEnabled: boolean;
  isConnected: boolean;
  connectionError: string | null;
  lastUpdate: string | null;
  
  // UI state
  isLoadingTraces: boolean;
  isLoadingTrace: boolean;
  error: string | null;
  
  // View state
  selectedTaskId: string | null;
  expandedPhases: Set<string>;
  expandedLLMCalls: Set<string>;
}

// Action types
export type TraceAction =
  | { type: 'SET_AVAILABLE_TRACES'; payload: string[] }
  | { type: 'SET_SELECTED_TRACE_ID'; payload: string | null }
  | { type: 'SET_CURRENT_TRACE'; payload: TraceSession | null }
  | { type: 'SET_REALTIME_ENABLED'; payload: boolean }
  | { type: 'SET_CONNECTION_STATE'; payload: { isConnected: boolean; error: string | null } }
  | { type: 'SET_LAST_UPDATE'; payload: string }
  | { type: 'SET_LOADING_TRACES'; payload: boolean }
  | { type: 'SET_LOADING_TRACE'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_SELECTED_TASK'; payload: string | null }
  | { type: 'TOGGLE_PHASE_EXPANDED'; payload: string }
  | { type: 'TOGGLE_LLM_CALL_EXPANDED'; payload: string }
  | { type: 'RESET_VIEW_STATE' }
  | { type: 'RESET_STATE' };

// Initial state
const initialState: TraceState = {
  availableTraces: [],
  selectedTraceId: null,
  currentTrace: null,
  isRealTimeEnabled: false,
  isConnected: false,
  connectionError: null,
  lastUpdate: null,
  isLoadingTraces: false,
  isLoadingTrace: false,
  error: null,
  selectedTaskId: null,
  expandedPhases: new Set(),
  expandedLLMCalls: new Set(),
};

// Reducer function
const traceReducer = (state: TraceState, action: TraceAction): TraceState => {
  switch (action.type) {
    case 'SET_AVAILABLE_TRACES':
      return {
        ...state,
        availableTraces: action.payload,
      };
    
    case 'SET_SELECTED_TRACE_ID':
      return {
        ...state,
        selectedTraceId: action.payload,
        // Reset trace-specific state when changing traces
        currentTrace: null,
        selectedTaskId: null,
        expandedPhases: new Set(),
        expandedLLMCalls: new Set(),
      };
    
    case 'SET_CURRENT_TRACE':
      return {
        ...state,
        currentTrace: action.payload,
      };
    
    case 'SET_REALTIME_ENABLED':
      return {
        ...state,
        isRealTimeEnabled: action.payload,
      };
    
    case 'SET_CONNECTION_STATE':
      return {
        ...state,
        isConnected: action.payload.isConnected,
        connectionError: action.payload.error,
      };
    
    case 'SET_LAST_UPDATE':
      return {
        ...state,
        lastUpdate: action.payload,
      };
    
    case 'SET_LOADING_TRACES':
      return {
        ...state,
        isLoadingTraces: action.payload,
      };
    
    case 'SET_LOADING_TRACE':
      return {
        ...state,
        isLoadingTrace: action.payload,
      };
    
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
    
    case 'SET_SELECTED_TASK':
      return {
        ...state,
        selectedTaskId: action.payload,
      };
    
    case 'TOGGLE_PHASE_EXPANDED':
      const newExpandedPhases = new Set(state.expandedPhases);
      if (newExpandedPhases.has(action.payload)) {
        newExpandedPhases.delete(action.payload);
      } else {
        newExpandedPhases.add(action.payload);
      }
      return {
        ...state,
        expandedPhases: newExpandedPhases,
      };
    
    case 'TOGGLE_LLM_CALL_EXPANDED':
      const newExpandedLLMCalls = new Set(state.expandedLLMCalls);
      if (newExpandedLLMCalls.has(action.payload)) {
        newExpandedLLMCalls.delete(action.payload);
      } else {
        newExpandedLLMCalls.add(action.payload);
      }
      return {
        ...state,
        expandedLLMCalls: newExpandedLLMCalls,
      };
    
    case 'RESET_VIEW_STATE':
      return {
        ...state,
        selectedTaskId: null,
        expandedPhases: new Set(),
        expandedLLMCalls: new Set(),
      };
    
    case 'RESET_STATE':
      return initialState;
    
    default:
      return state;
  }
};

// Context interface
interface TraceContextType {
  state: TraceState;
  dispatch: React.Dispatch<TraceAction>;
  realtimeService: RealtimeService;
  
  // Action creators
  setAvailableTraces: (traces: string[]) => void;
  setSelectedTraceId: (traceId: string | null) => void;
  setCurrentTrace: (trace: TraceSession | null) => void;
  setRealTimeEnabled: (enabled: boolean) => void;
  setConnectionState: (isConnected: boolean, error: string | null) => void;
  setLastUpdate: (timestamp: string) => void;
  setLoadingTraces: (isLoading: boolean) => void;
  setLoadingTrace: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  setSelectedTask: (taskId: string | null) => void;
  togglePhaseExpanded: (phaseId: string) => void;
  toggleLLMCallExpanded: (callId: string) => void;
  resetViewState: () => void;
  resetState: () => void;
  clearError: () => void;
}

// Create context
const TraceContext = createContext<TraceContextType | undefined>(undefined);

// Context provider props
interface TraceContextProviderProps {
  children: ReactNode;
  baseUrl?: string;
  initialState?: Partial<TraceState>;
}

// Context provider component
export const TraceContextProvider: React.FC<TraceContextProviderProps> = ({
  children,
  baseUrl = '',
  initialState: initialStateOverride,
}) => {
  const [state, dispatch] = useReducer(
    traceReducer,
    { ...initialState, ...initialStateOverride }
  );

  // Create realtime service instance once per baseUrl
  const realtimeService = useMemo(() => {
    console.log('[TraceContext] Creating RealtimeService for baseUrl:', baseUrl);
    return createRealtimeService(baseUrl);
  }, [baseUrl]);

  // Action creators
  const setAvailableTraces = useCallback((traces: string[]) => {
    dispatch({ type: 'SET_AVAILABLE_TRACES', payload: traces });
  }, []);

  const setSelectedTraceId = useCallback((traceId: string | null) => {
    dispatch({ type: 'SET_SELECTED_TRACE_ID', payload: traceId });
  }, []);

  const setCurrentTrace = useCallback((trace: TraceSession | null) => {
    dispatch({ type: 'SET_CURRENT_TRACE', payload: trace });
  }, []);

  const setRealTimeEnabled = useCallback((enabled: boolean) => {
    console.log('[TraceContext] setRealTimeEnabled:', enabled);
    // Pure state setter: actual start/stop is orchestrated by useRealtime hook
    dispatch({ type: 'SET_REALTIME_ENABLED', payload: enabled });
  }, []);

  const setConnectionState = useCallback((isConnected: boolean, error: string | null) => {
    dispatch({ type: 'SET_CONNECTION_STATE', payload: { isConnected, error } });
  }, []);

  const setLastUpdate = useCallback((timestamp: string) => {
    dispatch({ type: 'SET_LAST_UPDATE', payload: timestamp });
  }, []);

  const setLoadingTraces = useCallback((isLoading: boolean) => {
    dispatch({ type: 'SET_LOADING_TRACES', payload: isLoading });
  }, []);

  const setLoadingTrace = useCallback((isLoading: boolean) => {
    dispatch({ type: 'SET_LOADING_TRACE', payload: isLoading });
  }, []);

  const setError = useCallback((error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  }, []);

  const setSelectedTask = useCallback((taskId: string | null) => {
    dispatch({ type: 'SET_SELECTED_TASK', payload: taskId });
  }, []);

  const togglePhaseExpanded = useCallback((phaseId: string) => {
    dispatch({ type: 'TOGGLE_PHASE_EXPANDED', payload: phaseId });
  }, []);

  const toggleLLMCallExpanded = useCallback((callId: string) => {
    dispatch({ type: 'TOGGLE_LLM_CALL_EXPANDED', payload: callId });
  }, []);

  const resetViewState = useCallback(() => {
    dispatch({ type: 'RESET_VIEW_STATE' });
  }, []);

  const resetState = useCallback(() => {
    dispatch({ type: 'RESET_STATE' });
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: 'SET_ERROR', payload: null });
  }, []);

  // Cleanup realtime service on unmount
  useEffect(() => {
    return () => {
      console.log('[TraceContext] Provider unmount cleanup: stopping realtime monitoring');
      realtimeService.stopMonitoring();
    };
  }, [realtimeService]);

  const contextValue: TraceContextType = {
    state,
    dispatch,
    realtimeService,
    setAvailableTraces,
    setSelectedTraceId,
    setCurrentTrace,
    setRealTimeEnabled,
    setConnectionState,
    setLastUpdate,
    setLoadingTraces,
    setLoadingTrace,
    setError,
    setSelectedTask,
    togglePhaseExpanded,
    toggleLLMCallExpanded,
    resetViewState,
    resetState,
    clearError,
  };

  return (
    <TraceContext.Provider value={contextValue}>
      {children}
    </TraceContext.Provider>
  );
};

// Custom hook to use trace context
export const useTraceContext = (): TraceContextType => {
  const context = useContext(TraceContext);
  if (context === undefined) {
    throw new Error('useTraceContext must be used within a TraceContextProvider');
  }
  return context;
};

// Export context for testing purposes
export { TraceContext };
