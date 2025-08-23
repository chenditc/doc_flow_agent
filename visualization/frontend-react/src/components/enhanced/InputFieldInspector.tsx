import React, { useState } from 'react';
import type { JsonPathGeneration } from '../../types/trace';
import { InfoIconWithTooltip } from '../common/Tooltip';
import { ContextualLLMCall } from './ContextualLLMCall';

interface InputFieldInspectorProps {
  fieldName: string;
  description: string;
  jsonPathGeneration: JsonPathGeneration;
  contextData: Record<string, any>;
}

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  variant?: 'default' | 'success' | 'error' | 'info';
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({ 
  title, 
  children, 
  defaultExpanded = false,
  variant = 'default'
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return 'border-green-200 bg-green-50 hover:bg-green-100';
      case 'error':
        return 'border-red-200 bg-red-50 hover:bg-red-100';
      case 'info':
        return 'border-blue-200 bg-blue-50 hover:bg-blue-100';
      default:
        return 'border-gray-200 bg-gray-50 hover:bg-gray-100';
    }
  };

  return (
    <div className="border rounded-md">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full px-3 py-2 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors border-b border-gray-200 rounded-t-md text-sm ${getVariantStyles()}`}
      >
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900">{title}</span>
          <svg
            className={`h-4 w-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      
      {isExpanded && (
        <div className="p-3">
          {children}
        </div>
      )}
    </div>
  );
};

const JSONPathHighlighter: React.FC<{ path: string }> = ({ path }) => {
  // Simple JSON path syntax highlighting
  const highlightPath = (path: string) => {
    if (!path) return path;
    
    // Replace special characters with styled spans
    return path
      .replace(/\$\./g, '<span class="text-blue-600 font-semibold">$.</span>')
      .replace(/\['/g, '<span class="text-gray-600">[\'</span><span class="text-green-600">')
      .replace(/']/g, '</span><span class="text-gray-600">\']</span>')
      .replace(/\[(\d+)\]/g, '<span class="text-gray-600">[</span><span class="text-purple-600">$1</span><span class="text-gray-600">]</span>');
  };

  return (
    <code 
      className="text-sm font-mono bg-gray-100 px-2 py-1 rounded border"
      dangerouslySetInnerHTML={{ __html: highlightPath(path) }}
    />
  );
};

const ValueDisplay: React.FC<{ value: any; label: string }> = ({ value, label }) => {
  const getValueType = (val: any): string => {
    if (val === null) return 'null';
    if (val === undefined) return 'undefined';
    if (typeof val === 'string' && val === '<NOT_FOUND_IN_CANDIDATES>') return 'not_found';
    return typeof val;
  };

  const getValueColor = (type: string): string => {
    switch (type) {
      case 'string': return 'text-green-700';
      case 'number': return 'text-blue-700';
      case 'boolean': return 'text-purple-700';
      case 'object': return 'text-orange-700';
      case 'null': 
      case 'undefined': return 'text-gray-500';
      case 'not_found': return 'text-red-600';
      default: return 'text-gray-700';
    }
  };

  const formatValue = (val: any): string => {
    if (val === null) return 'null';
    if (val === undefined) return 'undefined';
    if (typeof val === 'object') {
      try {
        return JSON.stringify(val, null, 2);
      } catch {
        return '[Complex Object]';
      }
    }
    return String(val);
  };

  const valueType = getValueType(value);
  const isNotFound = valueType === 'not_found';
  
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={`text-xs px-2 py-1 rounded ${
          isNotFound ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'
        }`}>
          {valueType}
        </span>
      </div>
      <div className={`p-3 bg-white border rounded text-sm font-mono max-h-32 overflow-y-auto ${
        isNotFound ? 'border-red-200 bg-red-50' : 'border-gray-200'
      }`}>
        <pre className={`whitespace-pre-wrap ${getValueColor(valueType)}`}>
          {formatValue(value)}
        </pre>
      </div>
    </div>
  );
};

export const InputFieldInspector: React.FC<InputFieldInspectorProps> = ({ 
  fieldName, 
  description, 
  jsonPathGeneration,
  contextData 
}) => {
  const { generated_path, extracted_value, llm_calls, error } = jsonPathGeneration;
  
  const hasError = !!error;
  const isValueFound = extracted_value !== '<NOT_FOUND_IN_CANDIDATES>' && 
                      extracted_value !== null && 
                      extracted_value !== undefined;

  return (
    <div className="border rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className={`px-4 py-3 border-b ${
        hasError ? 'border-red-200 bg-red-50' : 
        isValueFound ? 'border-green-200 bg-green-50' : 'border-yellow-200 bg-yellow-50'
      }`}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-medium text-gray-900">{fieldName}</h4>
              <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                hasError ? 'bg-red-100 text-red-800' :
                isValueFound ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
              }`}>
                {hasError ? 'Error' : isValueFound ? 'Extracted' : 'Not Found'}
              </div>
            </div>
            {description && (
              <p className="text-sm text-gray-600">{description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Quick Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ValueDisplay 
            value={extracted_value} 
            label="Extracted Value" 
          />
          
          {generated_path && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Generated JSONPath</div>
              <div className="p-3 bg-gray-50 border rounded">
                <JSONPathHighlighter path={generated_path} />
              </div>
            </div>
          )}
        </div>

        {/* Error Display */}
        {hasError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded">
            <div className="flex items-start gap-2">
              <svg className="h-5 w-5 text-red-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h5 className="font-medium text-red-800 mb-1">Extraction Error</h5>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Expandable Sections */}
        <div className="space-y-3">
          {/* Context Preview */}
          <CollapsibleSection 
            title="Context Data Used" 
            variant="info"
            defaultExpanded={!isValueFound}
          >
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                Available context data that could be used for extraction:
              </p>
              <div className="bg-gray-50 border rounded p-3">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {JSON.stringify(contextData, null, 2)}
                </pre>
              </div>
            </div>
          </CollapsibleSection>

          {/* LLM Extraction Calls */}
          {llm_calls && llm_calls.length > 0 && (
            <CollapsibleSection 
              title={`Extraction LLM Calls (${llm_calls.length})`}
              variant="default"
              defaultExpanded={hasError}
            >
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  LLM calls made to generate the extraction logic for this field:
                </p>
                {llm_calls.map((call, index) => (
                  <div key={call.tool_call_id || index} className="border border-blue-200 rounded-lg">
                    <div className="px-3 py-2 bg-blue-50 border-b border-blue-200 rounded-t-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-blue-900">
                          Extraction Call {index + 1}
                        </span>
                        <span className="text-xs text-blue-600">
                          {call.step}
                        </span>
                      </div>
                    </div>
                    <div className="p-3">
                      <ContextualLLMCall 
                        llmCall={call}
                        context="field_extraction"
                        relatedData={{ fieldName, description }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Extraction Process Flow */}
          <CollapsibleSection title="Extraction Process" variant="default">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm font-medium text-gray-700">Process Steps:</span>
              <InfoIconWithTooltip 
                tooltip={
                  <div className="space-y-2">
                    <div>
                      <span className="font-medium">1. Context Analysis:</span>
                      <p className="text-sm mt-1">Available context fields were analyzed to identify potential data sources for the "{fieldName}" field.</p>
                    </div>
                    <div>
                      <span className="font-medium">2. Extraction Logic Generation:</span>
                      <p className="text-sm mt-1">
                        {llm_calls && llm_calls.length > 0 
                          ? `${llm_calls.length} LLM call(s) generated the extraction logic.`
                          : 'Direct extraction logic was used without LLM calls.'
                        }
                      </p>
                    </div>
                    <div>
                      <span className="font-medium">3. Value Extraction:</span>
                      <p className="text-sm mt-1">
                        {hasError 
                          ? 'Extraction failed with an error.'
                          : isValueFound 
                            ? 'Successfully extracted the field value from context.'
                            : 'Field value was not found in the available context.'
                        }
                      </p>
                    </div>
                  </div>
                }
              />
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">1</div>
                <span className="text-gray-600">Context Analysis</span>
              </div>
              <div className="text-gray-300">→</div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">2</div>
                <span className="text-gray-600">Logic Generation</span>
              </div>
              <div className="text-gray-300">→</div>
              <div className="flex items-center gap-2">
                <div className={`w-4 h-4 rounded-full flex items-center justify-center text-xs font-medium ${
                  hasError ? 'bg-red-100 text-red-600' : 
                  isValueFound ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'
                }`}>3</div>
                <span className={`${
                  hasError ? 'text-red-600' : 
                  isValueFound ? 'text-green-600' : 'text-yellow-600'
                }`}>
                  {hasError ? 'Failed' : isValueFound ? 'Success' : 'Not Found'}
                </span>
              </div>
            </div>
          </CollapsibleSection>
        </div>
      </div>
    </div>
  );
};
