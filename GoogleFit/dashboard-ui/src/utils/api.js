/**
 * API Client for Health Dashboard
 * Handles all communication with the Flask backend API
 */

const API_BASE_URL = 'http://localhost:5000/api';

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Make an API request with error handling
 */
async function apiRequest(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new APIError(
        data.message || 'API request failed',
        response.status,
        data
      );
    }

    return data;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    
    // Network or parsing error
    throw new APIError(
      'Network error or server unavailable',
      0,
      { originalError: error.message }
    );
  }
}

/**
 * Convert date range type to API parameter
 */
function dateRangeToQueryParam(rangeType) {
  const mapping = {
    'today': 'today',
    'yesterday': 'yesterday',
    'last_7_days': 'last_7_days',
    'last_30_days': 'last_30_days',
    'this_week': 'this_week',
    'this_month': 'this_month',
  };
  
  return mapping[rangeType] || 'today';
}

/**
 * Fetch Google Fit data
 */
export async function fetchGoogleFitData(dateRange) {
  const rangeParam = dateRangeToQueryParam(dateRange);
  
  try {
    const data = await apiRequest(`/google-fit?range_type=${rangeParam}`);
    return {
      success: true,
      data,
    };
  } catch (error) {
    console.error('Google Fit API error:', error);
    return {
      success: false,
      error: error.message,
      configured: error.data?.configured !== false,
    };
  }
}

/**
 * Fetch Google Fit data for a specific calendar day (for weekly chart).
 * @param {Date} date — the day to fetch
 */
export async function fetchGoogleFitDataForDate(date) {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  const end = new Date(date);
  end.setHours(23, 59, 59, 999);

  const startISO = start.toISOString();
  const endISO   = end.toISOString();

  try {
    const data = await apiRequest(
      `/google-fit?range_type=custom&start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`
    );
    return { success: true, data };
  } catch (error) {
    console.error(`Google Fit data for ${date.toDateString()}:`, error);
    return { success: false, error: error.message };
  }
}

/**
 * Fetch Strava data
 */
export async function fetchStravaData(dateRange) {
  const rangeParam = dateRangeToQueryParam(dateRange);
  
  try {
    const data = await apiRequest(`/strava?range_type=${rangeParam}`);
    return {
      success: true,
      data,
    };
  } catch (error) {
    console.error('Strava API error:', error);
    return {
      success: false,
      error: error.message,
      configured: error.data?.configured !== false,
    };
  }
}

/**
 * Check API health and configuration status
 */
export async function checkAPIStatus() {
  try {
    const [health, status] = await Promise.all([
      apiRequest('/health'),
      apiRequest('/status'),
    ]);
    
    return {
      healthy: true,
      googleFit: status.google_fit,
      strava: status.strava,
      timestamp: health.timestamp,
    };
  } catch (error) {
    console.error('API status check failed:', error);
    return {
      healthy: false,
      error: error.message,
    };
  }
}

/**
 * Retry wrapper for API calls
 */
export async function withRetry(apiCall, maxRetries = 2, delay = 1000) {
  let lastError;
  
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await apiCall();
    } catch (error) {
      lastError = error;
      
      // Don't retry on 401 (not configured) or 400 (bad request)
      if (error.status === 401 || error.status === 400) {
        throw error;
      }
      
      // Wait before retry (except on last attempt)
      if (i < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
      }
    }
  }
  
  throw lastError;
}
