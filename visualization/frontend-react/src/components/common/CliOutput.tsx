import React, { useState } from 'react';

interface CliOutputProps {
  stdout?: string;
  stderr?: string;
  title?: string;
}

export const CliOutput: React.FC<CliOutputProps> = ({ 
  stdout, 
  stderr, 
  title = "Command Output" 
}) => {
  const [activeTab, setActiveTab] = useState<'stdout' | 'stderr' | 'combined'>('combined');

  const hasStdout = stdout && stdout.trim().length > 0;
  const hasStderr = stderr && stderr.trim().length > 0;

  const getCombinedOutput = () => {
    let combined = '';
    if (hasStdout) {
      combined += stdout;
    }
    if (hasStderr) {
      if (combined) combined += '\n--- STDERR ---\n';
      combined += stderr;
    }
    return combined || 'No output';
  };

  const getActiveContent = () => {
    switch (activeTab) {
      case 'stdout':
        return stdout || 'No stdout';
      case 'stderr':
        return stderr || 'No stderr';
      case 'combined':
      default:
        return getCombinedOutput();
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(getActiveContent());
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  return (
    <div className="bg-gray-900 border rounded-md overflow-hidden">
      {/* Header with tabs */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="flex items-center justify-between px-3 py-2">
          <div className="flex space-x-1">
            <button
              onClick={() => setActiveTab('combined')}
              className={`px-3 py-1 text-xs font-medium rounded ${
                activeTab === 'combined'
                  ? 'bg-gray-700 text-green-400'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Combined
            </button>
            {hasStdout && (
              <button
                onClick={() => setActiveTab('stdout')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  activeTab === 'stdout'
                    ? 'bg-gray-700 text-green-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                stdout
              </button>
            )}
            {hasStderr && (
              <button
                onClick={() => setActiveTab('stderr')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  activeTab === 'stderr'
                    ? 'bg-gray-700 text-red-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                stderr
              </button>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-xs font-medium text-gray-400 uppercase">
              {title}
            </span>
            <button
              onClick={handleCopy}
              className="text-gray-400 hover:text-gray-200 focus:outline-none focus:text-gray-200"
              title="Copy to clipboard"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <pre className={`text-sm font-mono whitespace-pre-wrap break-words max-h-96 overflow-y-auto ${
          activeTab === 'stderr' ? 'text-red-300' : 'text-green-300'
        }`}>
          {getActiveContent()}
        </pre>
      </div>
    </div>
  );
};
