import React from 'react';

interface ParameterCardsProps {
  parameters: Record<string, any>;
}

export const ParameterCards: React.FC<ParameterCardsProps> = ({ parameters }) => {
  if (!parameters || typeof parameters !== 'object' || Object.keys(parameters).length === 0) {
    return (
      <div className="text-gray-500 text-sm">No parameters</div>
    );
  }

  const renderValue = (value: any): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>;
    }
    
    if (typeof value === 'string') {
      // Respect newline characters by using whitespace-pre-wrap
      return <div className="text-gray-900 whitespace-pre-wrap break-words">{value}</div>;
    }
    
    if (typeof value === 'number' || typeof value === 'boolean') {
      return <span className="text-blue-600 font-mono">{String(value)}</span>;
    }
    
    if (Array.isArray(value)) {
      return (
        <div className="space-y-1">
          {value.map((item, index) => (
            <div key={index} className="flex items-start gap-2">
              <span className="text-gray-400 text-xs mt-0.5">{index + 1}.</span>
              <div className="flex-1">{renderValue(item)}</div>
            </div>
          ))}
        </div>
      );
    }
    
    if (typeof value === 'object') {
      return (
        <pre className="text-xs bg-gray-100 rounded p-2 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    
    return <div className="text-gray-900 whitespace-pre-wrap break-words">{String(value)}</div>;
  };

  return (
    <div className="space-y-3">
      {Object.entries(parameters).map(([key, value]) => (
        <div key={key} className="bg-white border rounded-lg p-3 shadow-sm w-full">
          <div className="text-sm font-medium text-gray-700 mb-2 capitalize">
            {key.replace(/_/g, ' ')}
          </div>
          <div className="text-sm">
            {renderValue(value)}
          </div>
        </div>
      ))}
    </div>
  );
};
