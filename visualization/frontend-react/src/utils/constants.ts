/**
 * Application constants for Doc Flow Trace Viewer
 */

// API endpoints
export const API_ENDPOINTS = {
  TRACES: '/traces',
  TRACE_BY_ID: (id: string) => `/traces/${encodeURIComponent(id)}`,
  LATEST_TRACE: '/traces/latest',
  TRACE_STREAM: (id: string) => `/traces/${encodeURIComponent(id)}/stream`,
  HEALTH: '/health',
  TRACE_STATISTICS: (id: string) => `/traces/${encodeURIComponent(id)}/statistics`,
} as const;

// Local storage keys
export const STORAGE_KEYS = {
  USER_PREFERENCES: 'doc-flow-trace-viewer-preferences',
  SELECTED_TRACE: 'doc-flow-selected-trace',
  EXPANDED_PHASES: 'doc-flow-expanded-phases',
  EXPANDED_LLM_CALLS: 'doc-flow-expanded-llm-calls',
  THEME: 'doc-flow-theme',
} as const;

// Theme constants
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
} as const;

// Status colors
export const STATUS_COLORS = {
  completed: 'green',
  running: 'blue',
  error: 'red',
  cancelled: 'gray',
  pending: 'yellow',
} as const;

// Animation durations (in milliseconds)
export const ANIMATION_DURATIONS = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
} as const;

// Default intervals (in milliseconds)
export const INTERVALS = {
  AUTO_REFRESH: 5000,
  HEALTH_CHECK: 10000,
  RECONNECT: 5000,
} as const;

// Maximum values
export const LIMITS = {
  MAX_RECONNECT_ATTEMPTS: 5,
  MAX_TEXT_LENGTH: 1000,
  MAX_OUTPUT_PREVIEW: 500,
  MAX_PROMPT_PREVIEW: 300,
} as const;

// Phase names
export const PHASE_NAMES = {
  SOP_RESOLUTION: 'sop_resolution',
  TASK_CREATION: 'task_creation',
  TASK_EXECUTION: 'task_execution',
  CONTEXT_UPDATE: 'context_update',
  NEW_TASK_GENERATION: 'new_task_generation',
} as const;

// Phase display names
export const PHASE_DISPLAY_NAMES = {
  [PHASE_NAMES.SOP_RESOLUTION]: 'SOP Resolution',
  [PHASE_NAMES.TASK_CREATION]: 'Task Creation',
  [PHASE_NAMES.TASK_EXECUTION]: 'Task Execution',
  [PHASE_NAMES.CONTEXT_UPDATE]: 'Context Update',
  [PHASE_NAMES.NEW_TASK_GENERATION]: 'New Task Generation',
} as const;

// Task statuses
export const TASK_STATUSES = {
  RUNNING: 'running',
  COMPLETED: 'completed',
  ERROR: 'error',
  CANCELLED: 'cancelled',
  PENDING: 'pending',
} as const;

// View types
export const VIEW_TYPES = {
  TIMELINE: 'timeline',
  TABLE: 'table',
} as const;

// Error messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error occurred. Please check your connection.',
  PARSE_ERROR: 'Failed to parse server response.',
  NOT_FOUND: 'Requested resource not found.',
  UNAUTHORIZED: 'You are not authorized to access this resource.',
  SERVER_ERROR: 'Server error occurred. Please try again later.',
  TIMEOUT: 'Request timed out. Please try again.',
  UNKNOWN: 'An unknown error occurred.',
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  TRACE_LOADED: 'Trace loaded successfully.',
  CONNECTION_ESTABLISHED: 'Real-time connection established.',
  PREFERENCES_SAVED: 'Preferences saved successfully.',
} as const;

// Component sizes
export const SIZES = {
  SIDEBAR_WIDTH: '300px',
  HEADER_HEIGHT: '64px',
  FOOTER_HEIGHT: '40px',
  MODAL_MAX_WIDTH: '90vw',
  MODAL_MAX_HEIGHT: '90vh',
} as const;

// Breakpoints (matching Tailwind CSS)
export const BREAKPOINTS = {
  SM: '640px',
  MD: '768px',
  LG: '1024px',
  XL: '1280px',
  '2XL': '1536px',
} as const;

// Z-index levels
export const Z_INDEX = {
  DROPDOWN: 10,
  STICKY: 20,
  FIXED: 30,
  MODAL_BACKDROP: 40,
  MODAL: 50,
  POPOVER: 60,
  TOOLTIP: 70,
} as const;

// Query client defaults
export const QUERY_DEFAULTS = {
  STALE_TIME: 30000, // 30 seconds
  CACHE_TIME: 300000, // 5 minutes
  RETRY_DELAY: 1000,
  MAX_RETRIES: 3,
} as const;
