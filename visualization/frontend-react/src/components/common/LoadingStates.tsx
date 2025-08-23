/**
 * Enhanced loading components with different states and skeleton loaders
 */

import React from 'react';
import type { ReactNode } from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  className = '' 
}) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6', 
    lg: 'h-8 w-8',
    xl: 'h-12 w-12'
  };

  return (
    <svg 
      className={`animate-spin ${sizeClasses[size]} ${className}`}
      xmlns="http://www.w3.org/2000/svg" 
      fill="none" 
      viewBox="0 0 24 24"
    >
      <circle 
        className="opacity-25" 
        cx="12" 
        cy="12" 
        r="10" 
        stroke="currentColor" 
        strokeWidth="4"
      />
      <path 
        className="opacity-75" 
        fill="currentColor" 
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
};

interface LoadingStateProps {
  isLoading: boolean;
  error?: string | null;
  children: ReactNode;
  loadingComponent?: ReactNode;
  errorComponent?: ReactNode;
  minHeight?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  isLoading,
  error,
  children,
  loadingComponent,
  errorComponent,
  minHeight = 'min-h-32'
}) => {
  if (error) {
    return (
      <div className={`flex items-center justify-center ${minHeight}`}>
        {errorComponent || (
          <div className="text-center text-red-600">
            <svg className="mx-auto h-12 w-12 text-red-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <p className="text-sm font-medium">Error loading data</p>
            <p className="text-xs text-gray-500 mt-1">{error}</p>
          </div>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center ${minHeight}`}>
        {loadingComponent || (
          <div className="text-center">
            <LoadingSpinner size="lg" className="text-blue-600 mb-2" />
            <p className="text-sm text-gray-600">Loading...</p>
          </div>
        )}
      </div>
    );
  }

  return <>{children}</>;
};

// Skeleton loader components for better UX
export const SkeletonLine: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`animate-pulse bg-gray-200 h-4 rounded ${className}`} />
);

export const SkeletonBlock: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
);

interface SkeletonTimelineProps {
  items?: number;
}

export const SkeletonTimeline: React.FC<SkeletonTimelineProps> = ({ items = 5 }) => (
  <div className="space-y-4">
    {Array.from({ length: items }, (_, i) => (
      <div key={i} className="flex items-start space-x-3">
        <SkeletonBlock className="w-3 h-3 rounded-full mt-2" />
        <div className="flex-1 space-y-2">
          <SkeletonLine className="w-1/2" />
          <SkeletonLine className="w-3/4" />
        </div>
        <SkeletonLine className="w-16" />
      </div>
    ))}
  </div>
);

interface SkeletonModalProps {
  className?: string;
}

export const SkeletonModal: React.FC<SkeletonModalProps> = ({ className = '' }) => (
  <div className={`space-y-4 ${className}`}>
    <div className="space-y-2">
      <SkeletonLine className="w-1/3 h-6" />
      <SkeletonLine className="w-1/2 h-4" />
    </div>
    <div className="space-y-3">
      <SkeletonLine className="w-full" />
      <SkeletonLine className="w-5/6" />
      <SkeletonLine className="w-4/6" />
    </div>
    <div className="space-y-2">
      <SkeletonLine className="w-1/4 h-5" />
      <SkeletonBlock className="h-24" />
    </div>
  </div>
);

interface SkeletonCardProps {
  className?: string;
}

export const SkeletonCard: React.FC<SkeletonCardProps> = ({ className = '' }) => (
  <div className={`border rounded-lg p-4 space-y-3 ${className}`}>
    <div className="space-y-2">
      <SkeletonLine className="w-2/3 h-5" />
      <SkeletonLine className="w-1/2 h-4" />
    </div>
    <SkeletonBlock className="h-20" />
    <div className="flex space-x-2">
      <SkeletonBlock className="h-6 w-16" />
      <SkeletonBlock className="h-6 w-12" />
    </div>
  </div>
);
