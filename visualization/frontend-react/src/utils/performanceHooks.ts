/**
 * Performance optimization hooks and utilities
 */

import { useState, useMemo, useCallback, useRef, useEffect } from 'react';

/**
 * Deep equality comparison for object props
 */
export const deepEqual = (a: any, b: any): boolean => {
  if (a === b) return true;
  if (a == null || b == null) return false;
  if (typeof a !== typeof b) return false;
  
  if (typeof a === 'object') {
    if (Array.isArray(a) !== Array.isArray(b)) return false;
    
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    
    if (keysA.length !== keysB.length) return false;
    
    for (const key of keysA) {
      if (!keysB.includes(key) || !deepEqual(a[key], b[key])) {
        return false;
      }
    }
    
    return true;
  }
  
  return a === b;
};

/**
 * Shallow equality comparison for props
 */
export const shallowEqual = <T extends object>(a: T, b: T): boolean => {
  const keysA = Object.keys(a) as (keyof T)[];
  const keysB = Object.keys(b) as (keyof T)[];
  
  if (keysA.length !== keysB.length) return false;
  
  return keysA.every(key => a[key] === b[key]);
};

/**
 * Hook for debouncing values
 */
export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

/**
 * Hook for throttling function calls
 */
export const useThrottle = <T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): T => {
  const lastExecuted = useRef(0);
  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  return useCallback(
    ((...args: Parameters<T>) => {
      const now = Date.now();
      
      if (now - lastExecuted.current >= delay) {
        lastExecuted.current = now;
        return fn(...args);
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = setTimeout(() => {
          lastExecuted.current = Date.now();
          fn(...args);
        }, delay - (now - lastExecuted.current));
      }
    }) as T,
    [fn, delay]
  );
};

/**
 * Hook for memoizing expensive computations
 */
export const useExpensiveMemo = <T>(
  factory: () => T,
  deps: React.DependencyList,
  isExpensive = true
): T => {
  const memoizedValue = useMemo(() => {
    if (isExpensive) {
      console.time('ExpensiveMemo');
      const result = factory();
      console.timeEnd('ExpensiveMemo');
      return result;
    }
    return factory();
  }, deps);

  return memoizedValue;
};

/**
 * Intersection Observer hook for lazy loading and viewport detection
 */
export const useIntersectionObserver = (
  options: IntersectionObserverInit = {}
) => {
  const [isIntersecting, setIsIntersecting] = useState(false);
  const targetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = targetRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => setIsIntersecting(entry.isIntersecting),
      {
        threshold: 0.1,
        ...options,
      }
    );

    observer.observe(element);

    return () => {
      observer.unobserve(element);
      observer.disconnect();
    };
  }, [options]);

  return { targetRef, isIntersecting };
};

/**
 * Virtual scrolling hook for large lists
 */
interface VirtualScrollOptions {
  itemHeight: number;
  containerHeight: number;
  overscan?: number;
}

export const useVirtualScroll = <T>(
  items: T[],
  options: VirtualScrollOptions
) => {
  const [scrollTop, setScrollTop] = useState(0);
  const { itemHeight, containerHeight, overscan = 3 } = options;

  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const startIndex = Math.floor(scrollTop / itemHeight);
  const endIndex = Math.min(startIndex + visibleCount + overscan, items.length);

  const visibleItems = useMemo(() => {
    return items.slice(startIndex, endIndex).map((item, index) => ({
      item,
      index: startIndex + index,
      offsetTop: (startIndex + index) * itemHeight,
    }));
  }, [items, startIndex, endIndex, itemHeight]);

  const totalHeight = items.length * itemHeight;

  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  return {
    visibleItems,
    totalHeight,
    handleScroll,
    startIndex,
    endIndex,
  };
};

/**
 * Performance monitoring hook
 */
export const usePerformanceMonitor = (name: string, threshold = 100) => {
  const startTimeRef = useRef<number | undefined>(undefined);
  const warningShownRef = useRef(false);

  const startMeasure = useCallback(() => {
    startTimeRef.current = performance.now();
    warningShownRef.current = false;
  }, []);

  const endMeasure = useCallback(() => {
    if (startTimeRef.current) {
      const duration = performance.now() - startTimeRef.current;
      
      if (duration > threshold && !warningShownRef.current) {
        console.warn(`Performance warning: ${name} took ${duration.toFixed(2)}ms (threshold: ${threshold}ms)`);
        warningShownRef.current = true;
      }
      
      performance.mark(`${name}-end`);
      performance.measure(name, `${name}-start`, `${name}-end`);
      
      return duration;
    }
    return 0;
  }, [name, threshold]);

  useEffect(() => {
    performance.mark(`${name}-start`);
    startMeasure();
    
    return () => {
      endMeasure();
    };
  }, [name, startMeasure, endMeasure]);

  return { startMeasure, endMeasure };
};

/**
 * Component render tracker for debugging
 */
export const useRenderTracker = (componentName: string) => {
  const renderCount = useRef(0);
  const previousProps = useRef<any>(undefined);

  useEffect(() => {
    renderCount.current += 1;
    console.log(`${componentName} rendered ${renderCount.current} times`);
  });

  const trackProps = useCallback((props: any) => {
    if (previousProps.current) {
      const changedProps = Object.keys(props).filter(
        key => props[key] !== previousProps.current[key]
      );
      
      if (changedProps.length > 0) {
        console.log(`${componentName} props changed:`, changedProps);
      }
    }
    
    previousProps.current = props;
  }, [componentName]);

  return { renderCount: renderCount.current, trackProps };
};
