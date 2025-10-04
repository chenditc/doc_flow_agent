/**
 * Metadata Form Component
 * Structured form for editing SOP document YAML metadata
 */

import React, { useState } from 'react';
import type { SopDocMeta } from '../../types';
import './MetadataForm.css';

interface MetadataFormProps {
  meta: SopDocMeta;
  onChange: (meta: SopDocMeta) => void;
}

const VALID_TOOL_IDS = [
  'LLM',
  'PYTHON_EXECUTOR',
  'CLI',
  'USER',
  'WEB_USER_COMMUNICATE',
  'WEB_RESULT_DELIVERY',
  'TEMPLATE',
];

export const MetadataForm: React.FC<MetadataFormProps> = ({ meta, onChange }) => {
  const [jsonPathsExpanded, setJsonPathsExpanded] = useState(false);
  
  const updateMeta = (updates: Partial<SopDocMeta>) => {
    onChange({ ...meta, ...updates });
  };

  const updateTool = (updates: Partial<typeof meta.tool>) => {
    onChange({
      ...meta,
      tool: { ...meta.tool, ...updates },
    });
  };

  const updateToolParameters = (key: string, value: any) => {
    const params = meta.tool.parameters || {};
    onChange({
      ...meta,
      tool: {
        ...meta.tool,
        parameters: {
          ...params,
          [key]: value,
        },
      },
    });
  };

  const removeToolParameter = (key: string) => {
    const params = { ...(meta.tool.parameters || {}) };
    delete params[key];
    onChange({
      ...meta,
      tool: {
        ...meta.tool,
        parameters: params,
      },
    });
  };

  const updateInputJsonPath = (key: string, value: string) => {
    onChange({
      ...meta,
      input_json_path: {
        ...(meta.input_json_path || {}),
        [key]: value,
      },
    });
  };

  const removeInputJsonPath = (key: string) => {
    const paths = { ...(meta.input_json_path || {}) };
    delete paths[key];
    onChange({
      ...meta,
      input_json_path: paths,
    });
  };

  const updateInputDescription = (key: string, value: string) => {
    onChange({
      ...meta,
      input_description: {
        ...(meta.input_description || {}),
        [key]: value,
      },
    });
  };

  const removeInputDescription = (key: string) => {
    const descs = { ...(meta.input_description || {}) };
    delete descs[key];
    onChange({
      ...meta,
      input_description: descs,
    });
  };

  const updateAlias = (index: number, value: string) => {
    const aliases = [...meta.aliases];
    aliases[index] = value;
    onChange({ ...meta, aliases });
  };

  const addAlias = () => {
    onChange({ ...meta, aliases: [...meta.aliases, ''] });
  };

  const removeAlias = (index: number) => {
    const aliases = meta.aliases.filter((_, i) => i !== index);
    onChange({ ...meta, aliases });
  };

  const Tooltip: React.FC<{ text: string }> = ({ text }) => (
    <span className="tooltip-icon" title={text}>ⓘ</span>
  );

  return (
    <div className="metadata-form">
      {/* Doc ID */}
      <div className="form-field">
        <label>
          Doc ID <Tooltip text="Unique identifier (optional, defaults to file path)" />
        </label>
        <div className="field-content">
          <input
            type="text"
            value={meta.doc_id || ''}
            onChange={(e) => updateMeta({ doc_id: e.target.value })}
            placeholder="e.g., tools/bash"
          />
        </div>
      </div>

      {/* Description */}
      <div className="form-field required">
        <label>
          Description <Tooltip text="Brief description of what this document does" />
        </label>
        <div className="field-content">
          <textarea
            value={meta.description}
            onChange={(e) => updateMeta({ description: e.target.value })}
            placeholder="e.g., Execute bash commands in sandbox environment"
            rows={2}
            required
          />
        </div>
      </div>

      {/* Aliases */}
      {meta.aliases.length > 0 && (
      <div className="form-field">
        <label>
          Aliases <Tooltip text="Alternative names for this document" />
        </label>
        <div className="field-content">
        <div className="list-editor">
          {meta.aliases.map((alias, index) => (
            <div key={index} className="list-item">
              <input
                type="text"
                value={alias}
                onChange={(e) => updateAlias(index, e.target.value)}
                placeholder="alias"
              />
              <button
                type="button"
                className="btn-remove"
                onClick={() => removeAlias(index)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        </div>
      </div>
      )}

      {/* Tool */}
      <div className="form-section">
        <div className="section-header">
          <h4>Tool Configuration</h4>
          <div className="section-actions">
            {meta.aliases.length === 0 && (
              <button type="button" className="btn-add-inline" onClick={addAlias}>
                + Add Alias
              </button>
            )}
            {(!meta.tool.parameters || Object.keys(meta.tool.parameters).length === 0) && (
              <button
                type="button"
                className="btn-add-inline"
                onClick={() => {
                  const key = prompt('Parameter name:');
                  if (key) updateToolParameters(key, '');
                }}
              >
                + Add Parameter
              </button>
            )}
          </div>
        </div>

        <div className="form-field required">
          <label>
            Tool ID <Tooltip text="Which tool to execute" />
          </label>
          <div className="field-content">
          <select
            value={meta.tool.tool_id}
            onChange={(e) => updateTool({ tool_id: e.target.value })}
            required
          >
            <option value="">Select a tool...</option>
            {VALID_TOOL_IDS.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
          </div>
        </div>

        {meta.tool.parameters && Object.keys(meta.tool.parameters).length > 0 && (
        <div className="form-field">
          <label>
            Tool Parameters <Tooltip text="Key-value pairs for tool configuration. Use {parameters.section_name} to reference markdown sections." />
          </label>
          <div className="field-content">
          <div className="dict-editor">
            {Object.entries(meta.tool.parameters || {}).map(([key, value]) => (
              <div key={key} className="dict-item">
                <input
                  type="text"
                  value={key}
                  placeholder="key"
                  className="dict-key"
                  readOnly
                />
                <input
                  type="text"
                  value={typeof value === 'string' ? value : JSON.stringify(value)}
                  onChange={(e) => updateToolParameters(key, e.target.value)}
                  placeholder="value"
                  className="dict-value"
                />
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => removeToolParameter(key)}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          </div>
        </div>
        )}
      </div>

      {/* Input/Output Configuration */}
      <div className="form-section">
        <h4 className="collapsible-header" onClick={() => setJsonPathsExpanded(!jsonPathsExpanded)}>
          <span className={`collapse-icon ${jsonPathsExpanded ? 'expanded' : ''}`}>▶</span>
          Input/Output JSON Paths (Optional)
        </h4>

        {jsonPathsExpanded && (
          <>
        <div className="form-field">
          <label>
            Input JSON Paths <Tooltip text="Map input fields to JSON paths in context (e.g., $.task)" />
          </label>
          <div className="field-content">
          <div className="dict-editor">
            {Object.entries(meta.input_json_path || {}).map(([key, value]) => (
              <div key={key} className="dict-item">
                <input
                  type="text"
                  value={key}
                  placeholder="field name"
                  className="dict-key"
                  readOnly
                />
                <input
                  type="text"
                  value={value}
                  onChange={(e) => updateInputJsonPath(key, e.target.value)}
                  placeholder="$.path.to.value"
                  className="dict-value"
                />
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => removeInputJsonPath(key)}
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              type="button"
              className="btn-add"
              onClick={() => {
                const key = prompt('Field name:');
                if (key) updateInputJsonPath(key, '');
              }}
            >
              + Add Input Path
            </button>
          </div>
          </div>
        </div>

        <div className="form-field">
          <label>
            Output JSON Path <Tooltip text="Where to store the output in context" />
          </label>
          <div className="field-content">
          <input
            type="text"
            value={meta.output_json_path || ''}
            onChange={(e) => updateMeta({ output_json_path: e.target.value })}
            placeholder="$.result.output"
          />
          </div>
        </div>
          </>
        )}

      </div>

      {/* Other Configuration */}
      <div className="form-section">
        <h4>Other Configuration</h4>

        <div className="form-field">
          <label>
            Input Descriptions <Tooltip text="Semantic descriptions of expected inputs" />
          </label>
          <div className="field-content">
          <div className="dict-editor">
            {Object.entries(meta.input_description || {}).map(([key, value]) => (
              <div key={key} className="dict-item">
                <input
                  type="text"
                  value={key}
                  placeholder="field name"
                  className="dict-key"
                  readOnly
                />
                <input
                  type="text"
                  value={value}
                  onChange={(e) => updateInputDescription(key, e.target.value)}
                  placeholder="Description of this input"
                  className="dict-value"
                />
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => removeInputDescription(key)}
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              type="button"
              className="btn-add"
              onClick={() => {
                const key = prompt('Field name:');
                if (key) updateInputDescription(key, '');
              }}
            >
              + Add Input Description
            </button>
          </div>
          </div>
        </div>

        <div className="form-field">
          <label>
            Output Description <Tooltip text="Semantic description of the output" />
          </label>
          <div className="field-content">
          <input
            type="text"
            value={meta.output_description || ''}
            onChange={(e) => updateMeta({ output_description: e.target.value })}
            placeholder="Description of what this document outputs"
          />
          </div>
        </div>

        <div className="form-field">
          <label>
            Result Validation Rule <Tooltip text="Optional validation criteria for the result" />
          </label>
          <div className="field-content">
          <input
            type="text"
            value={meta.result_validation_rule || ''}
            onChange={(e) => updateMeta({ result_validation_rule: e.target.value })}
            placeholder="e.g., Only accept if result is not None..."
          />
          </div>
        </div>
      </div>
    </div>
  );
};
