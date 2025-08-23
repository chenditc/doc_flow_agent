import React from 'react';

interface RealtimeToggleProps {
  isEnabled: boolean;
  isConnected: boolean;
  onToggle: (enabled: boolean) => void;
  disabled?: boolean;
}

export const RealtimeToggle: React.FC<RealtimeToggleProps> = ({
  isEnabled,
  isConnected,
  onToggle,
  disabled = false
}) => {
  return (
    <div className="flex items-center space-x-3">
      <div className="flex items-center">
        <input
          id="realtime-toggle"
          type="checkbox"
          checked={isEnabled}
          onChange={(e) => onToggle(e.target.checked)}
          disabled={disabled}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
        />
        <label 
          htmlFor="realtime-toggle" 
          className="ml-2 block text-sm text-gray-700 select-none"
        >
          Real-time Updates
        </label>
      </div>
      
      {/* Live indicator */}
      {isEnabled && (
        <div className="flex items-center space-x-2">
          <div 
            className={`h-2 w-2 rounded-full ${
              isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
            }`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
          <span className="text-xs text-gray-600">
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
      )}
    </div>
  );
};
