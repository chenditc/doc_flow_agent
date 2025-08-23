/**
 * Performance optimization components
 */

import React, { memo, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useIntersectionObserver } from '../../utils/performanceHooks';

/**
 * Memoized component wrapper with custom comparison
 */
export const withMemo = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  propsAreEqual?: (prevProps: P, nextProps: P) => boolean
) => {
  const MemoizedComponent = memo(WrappedComponent, propsAreEqual);
  MemoizedComponent.displayName = `withMemo(${WrappedComponent.displayName || WrappedComponent.name})`;
  return MemoizedComponent;
};

/**
 * Lazy loading wrapper component
 */
interface LazyLoadProps {
  children: ReactNode;
  fallback?: ReactNode;
  rootMargin?: string;
  threshold?: number;
  triggerOnce?: boolean;
}

export const LazyLoad: React.FC<LazyLoadProps> = ({
  children,
  fallback,
  rootMargin = '50px',
  threshold = 0.1,
  triggerOnce = true,
}) => {
  const [hasLoaded, setHasLoaded] = useState(false);
  const { targetRef, isIntersecting } = useIntersectionObserver({
    rootMargin,
    threshold,
  });

  useEffect(() => {
    if (isIntersecting && !hasLoaded) {
      setHasLoaded(true);
    }
  }, [isIntersecting, hasLoaded]);

  const shouldShow = triggerOnce ? hasLoaded : isIntersecting;

  return (
    <div ref={targetRef}>
      {shouldShow ? children : (fallback || <div className="h-32" />)}
    </div>
  );
};

/**
 * Code splitting boundary for lazy loading heavy components
 */
interface CodeSplitBoundaryProps {
  children: ReactNode;
  loading?: ReactNode;
  error?: ReactNode;
  onError?: (error: Error) => void;
}

export const CodeSplitBoundary: React.FC<CodeSplitBoundaryProps> = ({
  children,
  loading,
  error,
  onError
}) => {
  return (
    <React.Suspense
      fallback={loading || <div className="flex justify-center items-center h-32">Loading...</div>}
    >
      <ErrorBoundary onError={onError} fallback={error}>
        {children}
      </ErrorBoundary>
    </React.Suspense>
  );
};

// Simple error boundary for code splitting
class ErrorBoundary extends React.Component<
  { children: ReactNode; onError?: (error: Error) => void; fallback?: ReactNode },
  { hasError: boolean }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    if (this.props.onError) {
      this.props.onError(error);
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <div className="text-red-600">Something went wrong.</div>;
    }

    return this.props.children;
  }
}
