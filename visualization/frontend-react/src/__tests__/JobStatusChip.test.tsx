/**
 * Unit tests for JobStatusChip component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { JobStatusChip } from '../components/Jobs/JobStatusChip';
import type { JobStatus } from '../types';

describe('JobStatusChip', () => {
  const testCases: Array<{ status: JobStatus; expectedLabel: string }> = [
    { status: 'QUEUED', expectedLabel: 'Queued' },
    { status: 'STARTING', expectedLabel: 'Starting' },
    { status: 'RUNNING', expectedLabel: 'Running' },
    { status: 'COMPLETED', expectedLabel: 'Completed' },
    { status: 'FAILED', expectedLabel: 'Failed' },
    { status: 'CANCELLED', expectedLabel: 'Cancelled' },
  ];

  testCases.forEach(({ status, expectedLabel }) => {
    it(`should render ${status} status correctly`, () => {
      render(<JobStatusChip status={status} />);
      
      const chip = screen.getByText(expectedLabel);
      expect(chip).toBeInTheDocument();
    });
  });

  it('should render with small size by default', () => {
    render(<JobStatusChip status="RUNNING" />);
    
    const chip = screen.getByText('Running');
    expect(chip).toBeInTheDocument();
  });

  it('should render with medium size when specified', () => {
    render(<JobStatusChip status="RUNNING" size="medium" />);
    
    const chip = screen.getByText('Running');
    expect(chip).toBeInTheDocument();
  });

  it('should render with filled variant by default', () => {
    render(<JobStatusChip status="COMPLETED" />);
    
    const chip = screen.getByText('Completed');
    expect(chip).toBeInTheDocument();
  });

  it('should render with outlined variant when specified', () => {
    render(<JobStatusChip status="COMPLETED" variant="outlined" />);
    
    const chip = screen.getByText('Completed');
    expect(chip).toBeInTheDocument();
  });

  it('should apply running animation styles for RUNNING status', () => {
    render(<JobStatusChip status="RUNNING" />);
    
    const chip = screen.getByText('Running');
    expect(chip).toBeInTheDocument();
    
    // Check if the keyframes animation is injected
    const styleElements = document.querySelectorAll('style');
    const hasAnimationStyle = Array.from(styleElements).some(style => 
      style.textContent?.includes('@keyframes pulse')
    );
    expect(hasAnimationStyle).toBe(true);
  });

  it('should not apply running animation styles for non-RUNNING status', () => {
    // Clear any existing styles first
    document.querySelectorAll('style').forEach(style => style.remove());
    
    render(<JobStatusChip status="COMPLETED" />);
    
    const chip = screen.getByText('Completed');
    expect(chip).toBeInTheDocument();
    
    // Check that no animation style is injected
    const styleElements = document.querySelectorAll('style');
    const hasAnimationStyle = Array.from(styleElements).some(style => 
      style.textContent?.includes('@keyframes pulse')
    );
    expect(hasAnimationStyle).toBe(false);
  });
});