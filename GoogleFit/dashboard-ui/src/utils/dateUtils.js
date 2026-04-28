/**
 * Date utility functions for date range selection
 */

export const DATE_RANGES = {
  TODAY: 'today',
  YESTERDAY: 'yesterday',
  LAST_7_DAYS: 'last_7_days',
  LAST_30_DAYS: 'last_30_days',
  THIS_WEEK: 'this_week',
  THIS_MONTH: 'this_month',
  CUSTOM: 'custom'
};

export const DATE_RANGE_LABELS = {
  [DATE_RANGES.TODAY]: 'Today',
  [DATE_RANGES.YESTERDAY]: 'Yesterday',
  [DATE_RANGES.LAST_7_DAYS]: 'Last 7 Days',
  [DATE_RANGES.LAST_30_DAYS]: 'Last 30 Days',
  [DATE_RANGES.THIS_WEEK]: 'This Week',
  [DATE_RANGES.THIS_MONTH]: 'This Month',
  [DATE_RANGES.CUSTOM]: 'Custom Range'
};

/**
 * Get start and end of today (00:00:00 to 23:59:59)
 */
export const getToday = () => {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  
  const end = new Date();
  end.setHours(23, 59, 59, 999);
  
  return { start, end };
};

/**
 * Get start and end of yesterday
 */
export const getYesterday = () => {
  const start = new Date();
  start.setDate(start.getDate() - 1);
  start.setHours(0, 0, 0, 0);
  
  const end = new Date();
  end.setDate(end.getDate() - 1);
  end.setHours(23, 59, 59, 999);
  
  return { start, end };
};

/**
 * Get last N days (including today)
 */
export const getLastNDays = (days) => {
  const end = new Date();
  end.setHours(23, 59, 59, 999);
  
  const start = new Date();
  start.setDate(start.getDate() - (days - 1));
  start.setHours(0, 0, 0, 0);
  
  return { start, end };
};

/**
 * Get current week (Monday to Sunday)
 */
export const getThisWeek = () => {
  const now = new Date();
  const dayOfWeek = now.getDay();
  const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Adjust for Monday start
  
  const start = new Date(now);
  start.setDate(now.getDate() + diff);
  start.setHours(0, 0, 0, 0);
  
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  end.setHours(23, 59, 59, 999);
  
  return { start, end };
};

/**
 * Get current month
 */
export const getThisMonth = () => {
  const now = new Date();
  
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  start.setHours(0, 0, 0, 0);
  
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  end.setHours(23, 59, 59, 999);
  
  return { start, end };
};

/**
 * Get date range based on preset
 */
export const getDateRange = (rangeType) => {
  switch (rangeType) {
    case DATE_RANGES.TODAY:
      return getToday();
    case DATE_RANGES.YESTERDAY:
      return getYesterday();
    case DATE_RANGES.LAST_7_DAYS:
      return getLastNDays(7);
    case DATE_RANGES.LAST_30_DAYS:
      return getLastNDays(30);
    case DATE_RANGES.THIS_WEEK:
      return getThisWeek();
    case DATE_RANGES.THIS_MONTH:
      return getThisMonth();
    default:
      return getToday();
  }
};

/**
 * Format date range for display
 */
export const formatDateRange = (start, end) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const startDate = new Date(start);
  startDate.setHours(0, 0, 0, 0);
  
  const endDate = new Date(end);
  endDate.setHours(0, 0, 0, 0);
  
  // Check if it's today
  if (startDate.getTime() === today.getTime() && endDate.getTime() === today.getTime()) {
    return 'Today';
  }
  
  // Format as "MMM DD" or "MMM DD - MMM DD"
  const formatDate = (date) => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}`;
  };
  
  if (startDate.getTime() === endDate.getTime()) {
    return formatDate(startDate);
  }
  
  return `${formatDate(startDate)} - ${formatDate(endDate)}`;
};
