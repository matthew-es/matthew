import { reportWebVitals, createWebVitalsHandler } from './report-web-vitals';

// Performance monitoring utilities
const performanceMonitoring = {
  // Start web vitals monitoring
  startWebVitals: (customHandler?: (metric: any) => void) => {
    reportWebVitals(customHandler);
  },

  // Manual performance mark
  mark: (name: string) => {
    if (typeof performance !== 'undefined' && performance.mark) {
      performance.mark(name);
    }
  },

  // Manual performance measure
  measure: (name: string, startMark: string, endMark?: string) => {
    if (typeof performance !== 'undefined' && performance.measure) {
      performance.measure(name, startMark, endMark);
    }
  },

  // Get performance entries
  getEntries: (type?: string) => {
    if (typeof performance !== 'undefined' && performance.getEntriesByType) {
      return type ? performance.getEntriesByType(type) : performance.getEntries();
    }
    return [];
  }
};

export { reportWebVitals, createWebVitalsHandler, performanceMonitoring };