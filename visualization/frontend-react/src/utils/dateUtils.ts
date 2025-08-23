/**
 * Date and time utilities for Doc Flow Trace Viewer
 */

/**
 * Format date for display
 */
export const formatDate = (date: Date | string | null): string => {
  if (!date) return 'N/A';
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return dateObj.toLocaleDateString();
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Check if a date is today
 */
export const isToday = (date: Date | string): boolean => {
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const today = new Date();
    
    return dateObj.toDateString() === today.toDateString();
  } catch (error) {
    return false;
  }
};

/**
 * Check if a date is yesterday
 */
export const isYesterday = (date: Date | string): boolean => {
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    
    return dateObj.toDateString() === yesterday.toDateString();
  } catch (error) {
    return false;
  }
};

/**
 * Get smart date format (Today, Yesterday, or date)
 */
export const getSmartDateFormat = (date: Date | string | null): string => {
  if (!date) return 'N/A';
  
  try {
    if (isToday(date)) {
      return 'Today';
    } else if (isYesterday(date)) {
      return 'Yesterday';
    } else {
      return formatDate(date);
    }
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Parse ISO timestamp and return Date object
 */
export const parseTimestamp = (timestamp: string | null): Date | null => {
  if (!timestamp) return null;
  
  try {
    return new Date(timestamp);
  } catch (error) {
    return null;
  }
};

/**
 * Get time zone offset string
 */
export const getTimezoneOffset = (): string => {
  const offset = new Date().getTimezoneOffset();
  const hours = Math.abs(Math.floor(offset / 60));
  const minutes = Math.abs(offset % 60);
  const sign = offset <= 0 ? '+' : '-';
  
  return `${sign}${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
};

/**
 * Convert timestamp to user's local timezone
 */
export const toLocalTime = (timestamp: string | null): Date | null => {
  if (!timestamp) return null;
  
  try {
    return new Date(timestamp);
  } catch (error) {
    return null;
  }
};
