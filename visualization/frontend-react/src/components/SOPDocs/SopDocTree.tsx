/**
 * SOP Document Tree Component
 * Displays the directory tree with collapsible folders
 */

import React, { useState, useMemo } from 'react';
import type { TreeNode, SearchResponse } from '../../types';
import './SopDocTree.css';

interface SopDocTreeProps {
  tree: TreeNode[];
  selectedPath?: string;
  onSelectDoc: (path: string) => void;
  searchResults?: SearchResponse | null;
  loading?: boolean;
}

export const SopDocTree: React.FC<SopDocTreeProps> = ({
  tree,
  selectedPath,
  onSelectDoc,
  searchResults,
  loading = false,
}) => {
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());

  // Filter tree based on search results
  const filteredTree = useMemo(() => {
    if (!searchResults || searchResults.results.length === 0) {
      return tree;
    }

    const matchingPaths = new Set(searchResults.results.map(r => r.path));
    
    const filterNodes = (nodes: TreeNode[]): TreeNode[] => {
      return nodes
        .map(node => {
          if (node.type === 'file') {
            return matchingPaths.has(node.path) ? node : null;
          } else {
            // Directory - recursively filter children
            const filteredChildren = node.children ? filterNodes(node.children) : [];
            if (filteredChildren.length > 0) {
              return {
                ...node,
                children: filteredChildren,
              };
            }
            return null;
          }
        })
        .filter((node): node is TreeNode => node !== null);
    };

    return filterNodes(tree);
  }, [tree, searchResults]);

  // Auto-expand directories when search is active
  React.useEffect(() => {
    if (searchResults && searchResults.results.length > 0) {
      const newExpanded = new Set<string>();
      
      const expandParents = (nodes: TreeNode[]) => {
        nodes.forEach(node => {
          const currentPath = node.path;
          if (node.type === 'dir') {
            newExpanded.add(currentPath);
            if (node.children) {
              expandParents(node.children);
            }
          }
        });
      };
      
      expandParents(filteredTree);
      setExpandedDirs(newExpanded);
    }
  }, [searchResults, filteredTree]);

  const toggleDir = (path: string) => {
    setExpandedDirs(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const renderNode = (node: TreeNode, level: number = 0): React.ReactNode => {
    const isExpanded = expandedDirs.has(node.path);
    const isSelected = node.doc && node.path === selectedPath;
    const indent = level * 16;

    if (node.type === 'dir') {
      return (
        <div key={node.path} className="tree-node-wrapper">
          <div
            className={`tree-node tree-dir ${isExpanded ? 'expanded' : ''}`}
            style={{ paddingLeft: `${indent}px` }}
            onClick={() => toggleDir(node.path)}
          >
            <span className="tree-icon">{isExpanded ? '▼' : '▶'}</span>
            <span className="tree-name">{node.name}</span>
          </div>
          {isExpanded && node.children && (
            <div className="tree-children">
              {node.children.map(child => renderNode(child, level + 1))}
            </div>
          )}
        </div>
      );
    } else {
      return (
        <div
          key={node.path}
          className={`tree-node tree-file ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${indent + 16}px` }}
          onClick={() => onSelectDoc(node.path)}
        >
          <span className="tree-icon">📄</span>
          <span className="tree-name">{node.name}</span>
        </div>
      );
    }
  };

  if (loading) {
    return <div className="tree-loading">Loading...</div>;
  }

  if (filteredTree.length === 0) {
    return (
      <div className="tree-empty">
        {searchResults ? 'No matching documents found' : 'No documents found'}
      </div>
    );
  }

  return (
    <div className="sop-doc-tree">
      {filteredTree.map(node => renderNode(node))}
    </div>
  );
};
