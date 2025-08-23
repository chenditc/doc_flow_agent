/**
 * Connection status indicator for real-time updates
 */

import React from 'react';

interface ConnectionStatusProps {
  isConnected: boolean;
  error?: string;
  isEnabled: boolean;
  className?: string;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  isConnected,
  error,
  isEnabled,
  className = ''
}) => {
  if (!isEnabled) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="w-2 h-2 bg-gray-400 rounded-full" />
        <span className="text-sm text-gray-600">Real-time disabled</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center space-x-2 ${className}`} title={error}>
        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
        <span className="text-sm text-red-600">Connection error</span>
      </div>
    );
  }

  if (isConnected) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
        <span className="text-sm text-green-700">Connected</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
      <span className="text-sm text-yellow-700">Connecting...</span>
    </div>
  );
};

interface LiveIndicatorProps {
  isLive: boolean;
  lastUpdate?: string;
  className?: string;
}

export const LiveIndicator: React.FC<LiveIndicatorProps> = ({
  isLive,
  lastUpdate,
  className = ''
}) => {
  if (!isLive) {
    return null;
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <div className="flex items-center space-x-1">
        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
        <span className="text-xs font-medium text-red-600 uppercase tracking-wide">LIVE</span>
      </div>
      {lastUpdate && (
        <span className="text-xs text-gray-500">
          Updated {new Date(lastUpdate).toLocaleTimeString()}
        </span>
      )}
    </div>
  );
};

interface RealtimeToggleProps {
  isEnabled: boolean;
  isConnected: boolean;
  error?: string;
  onToggle: () => void;
  disabled?: boolean;
  className?: string;
}

export const RealtimeToggle: React.FC<RealtimeToggleProps> = ({
  isEnabled,
  isConnected,
  error,
  onToggle,
  disabled = false,
  className = ''
}) => {
  const getStatusColor = () => {
    if (!isEnabled) return 'bg-gray-200';
    if (error) return 'bg-red-500';
    if (isConnected) return 'bg-green-500';
    return 'bg-yellow-500';
  };

  const getToggleColor = () => {
    if (disabled) return 'bg-gray-300';
    return isEnabled ? 'bg-blue-600' : 'bg-gray-200';
  };

  const getSwitchPosition = () => {
    return isEnabled ? 'translate-x-5' : 'translate-x-0';
  };

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      <label className="flex items-center space-x-2">
        <span className="text-sm font-medium text-gray-700">Real-time</span>
        <button
          type="button"
          onClick={onToggle}
          disabled={disabled}
          className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${getToggleColor()} ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
        >
          <span
            className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${getSwitchPosition()}`}
          />
        </button>
      </label>
      
      <div className="flex items-center space-x-1">
        <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
        <span className="text-xs text-gray-600">
          {!isEnabled ? 'Disabled' : error ? 'Error' : isConnected ? 'Connected' : 'Connecting'}
        </span>
      </div>
    </div>
  );
};
