/**
 * Job status chip component with consistent color coding
 */

import React from 'react';
import { Chip } from '@mui/material';
import type { JobStatus } from '../../types';

interface JobStatusChipProps {
  status: JobStatus;
  size?: 'small' | 'medium';
  variant?: 'filled' | 'outlined';
}

const statusConfig: Record<JobStatus, { color: string; bgColor: string; label: string }> = {
  QUEUED: {
    color: '#374151',
    bgColor: '#f3f4f6',
    label: 'Queued'
  },
  STARTING: {
    color: '#0369a1',
    bgColor: '#e0f2fe',
    label: 'Starting'
  },
  RUNNING: {
    color: '#1d4ed8',
    bgColor: '#dbeafe',
    label: 'Running'
  },
  COMPLETED: {
    color: '#15803d',
    bgColor: '#dcfce7',
    label: 'Completed'
  },
  FAILED: {
    color: '#dc2626',
    bgColor: '#fee2e2',
    label: 'Failed'
  },
  CANCELLED: {
    color: '#ea580c',
    bgColor: '#fed7aa',
    label: 'Cancelled'
  }
};

export const JobStatusChip: React.FC<JobStatusChipProps> = ({ 
  status, 
  size = 'small',
  variant = 'filled'
}) => {
  const config = statusConfig[status];
  
  const chipStyle = variant === 'filled' ? {
    backgroundColor: config.bgColor,
    color: config.color,
    fontWeight: 600,
    border: `1px solid ${config.color}20`,
  } : {
    color: config.color,
    borderColor: config.color,
    fontWeight: 600,
  };

  // Add pulsing animation for running status
  const isRunning = status === 'RUNNING';
  const pulseStyle = isRunning ? {
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  } : {};

  return (
    <>
      {isRunning && (
        <style>
          {`
            @keyframes pulse {
              0%, 100% {
                opacity: 1;
              }
              50% {
                opacity: .7;
              }
            }
          `}
        </style>
      )}
      <Chip
        label={config.label}
        size={size}
        variant={variant}
        sx={{
          ...chipStyle,
          ...pulseStyle,
          '& .MuiChip-label': {
            fontSize: size === 'small' ? '0.75rem' : '0.875rem',
          }
        }}
      />
    </>
  );
};