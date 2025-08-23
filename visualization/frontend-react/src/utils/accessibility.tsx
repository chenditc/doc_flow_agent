/**
 * Accessibility utilities and custom hooks
 */

import React, { useEffect, useRef } from 'react';

/**
 * Hook to manage focus trap for modals and dialogs
 */
export const useFocusTrap = (isActive: boolean) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as NodeListOf<HTMLElement>;

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus the first element initially
    firstElement.focus();

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    const handleEscapeKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Let parent components handle escape
        e.stopPropagation();
      }
    };

    document.addEventListener('keydown', handleTabKey);
    document.addEventListener('keydown', handleEscapeKey);

    return () => {
      document.removeEventListener('keydown', handleTabKey);
      document.removeEventListener('keydown', handleEscapeKey);
    };
  }, [isActive]);

  return containerRef;
};

/**
 * Hook to announce content changes to screen readers
 */
export const useAnnouncement = () => {
  const announcerRef = useRef<HTMLDivElement>(null);

  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (!announcerRef.current) return;

    // Clear previous announcement
    announcerRef.current.textContent = '';
    announcerRef.current.setAttribute('aria-live', priority);

    // Add new announcement after a brief delay to ensure screen readers pick it up
    setTimeout(() => {
      if (announcerRef.current) {
        announcerRef.current.textContent = message;
      }
    }, 100);
  };

  const AnnouncerComponent = () => (
    <div
      ref={announcerRef}
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    />
  );

  return { announce, AnnouncerComponent };
};

/**
 * Hook for keyboard navigation handling
 */
export const useKeyboardNavigation = (
  items: HTMLElement[],
  onSelect?: (index: number) => void,
  onEscape?: () => void
) => {
  const activeIndexRef = useRef(0);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (items.length === 0) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          activeIndexRef.current = (activeIndexRef.current + 1) % items.length;
          items[activeIndexRef.current]?.focus();
          break;

        case 'ArrowUp':
          e.preventDefault();
          activeIndexRef.current = activeIndexRef.current === 0 
            ? items.length - 1 
            : activeIndexRef.current - 1;
          items[activeIndexRef.current]?.focus();
          break;

        case 'Enter':
        case ' ':
          e.preventDefault();
          if (onSelect) {
            onSelect(activeIndexRef.current);
          }
          break;

        case 'Escape':
          e.preventDefault();
          if (onEscape) {
            onEscape();
          }
          break;

        case 'Home':
          e.preventDefault();
          activeIndexRef.current = 0;
          items[0]?.focus();
          break;

        case 'End':
          e.preventDefault();
          activeIndexRef.current = items.length - 1;
          items[items.length - 1]?.focus();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [items, onSelect, onEscape]);

  return activeIndexRef;
};

/**
 * Generate unique IDs for accessibility attributes
 */
let idCounter = 0;
export const useUniqueId = (prefix = 'id') => {
  const idRef = useRef<string | undefined>(undefined);
  
  if (!idRef.current) {
    idRef.current = `${prefix}-${++idCounter}`;
  }
  
  return idRef.current;
};

/**
 * Screen reader only text component
 */
export const VisuallyHidden: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="sr-only">{children}</span>
);

/**
 * Accessible skip link component
 */
interface SkipLinkProps {
  href: string;
  children: React.ReactNode;
  className?: string;
}

export const SkipLink: React.FC<SkipLinkProps> = ({ href, children, className = '' }) => (
  <a
    href={href}
    className={`sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded focus:shadow-lg ${className}`}
  >
    {children}
  </a>
);

/**
 * ARIA utilities
 */
export const aria = {
  /**
   * Create ARIA label props
   */
  label: (label: string) => ({ 'aria-label': label }),
  
  /**
   * Create ARIA described-by props
   */
  describedBy: (id: string) => ({ 'aria-describedby': id }),
  
  /**
   * Create ARIA labelled-by props
   */
  labelledBy: (id: string) => ({ 'aria-labelledby': id }),
  
  /**
   * Create ARIA expanded props
   */
  expanded: (isExpanded: boolean) => ({ 'aria-expanded': isExpanded }),
  
  /**
   * Create ARIA selected props
   */
  selected: (isSelected: boolean) => ({ 'aria-selected': isSelected }),
  
  /**
   * Create ARIA pressed props for toggle buttons
   */
  pressed: (isPressed: boolean) => ({ 'aria-pressed': isPressed }),
  
  /**
   * Create ARIA live region props
   */
  live: (politeness: 'polite' | 'assertive' | 'off' = 'polite') => ({
    'aria-live': politeness,
    'aria-atomic': true,
  }),
  
  /**
   * Create ARIA busy props
   */
  busy: (isBusy: boolean) => ({ 'aria-busy': isBusy }),
  
  /**
   * Create ARIA hidden props
   */
  hidden: (isHidden: boolean) => ({ 'aria-hidden': isHidden }),
};
