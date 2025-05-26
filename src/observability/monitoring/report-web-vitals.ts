import { onCLS, onFCP, onLCP, onTTFB, onINP, type Metric } from 'web-vitals';
import * as Sentry from "@sentry/react";

// Get the correct unit for each web vital
const getMetricUnit = (metricName: string): string => {
  switch (metricName) {
    case 'CLS':
      return 'unitless'; // Cumulative Layout Shift is unitless
    case 'FCP':
    case 'LCP':
    case 'TTFB':
    case 'INP':
    case 'FID': // Just in case
      return 'millisecond';
    default:
      return 'millisecond';
  }
};

// Enhanced web vitals handler that works with Sentry
const createWebVitalsHandler = () => {
  return (metric: Metric) => {
    const unit = getMetricUnit(metric.name);
    
    // ALWAYS send to Sentry (both dev and prod)
    Sentry.setMeasurement(metric.name, metric.value, unit);
    
    Sentry.addBreadcrumb({
      message: `Web Vital: ${metric.name}`,
      data: { 
        value: metric.value, 
        rating: metric.rating,
        delta: metric.delta,
        unit,
        environment: import.meta.env.MODE
      },
      level: metric.rating === 'good' ? 'info' : 'warning'
    });

    // Log poor performance as warnings
    if (metric.rating === 'poor') {
      Sentry.captureMessage(
        `Poor ${metric.name} performance: ${metric.value}${unit === 'unitless' ? '' : unit}`,
        'warning'
      );
    }
    
    // ALSO log to console in development for immediate feedback
    if (import.meta.env.DEV) {
      console.log(`${metric.name}:`, {
        value: metric.value,
        rating: metric.rating,
        delta: metric.delta,
        unit
      });
    }
  };
};


const reportWebVitals = (onPerfEntry?: (metric: Metric) => void) => {
  const handler = onPerfEntry || createWebVitalsHandler();
  
  if (handler && handler instanceof Function) {
    onCLS(handler);
    onFCP(handler);
    onLCP(handler);
    onTTFB(handler);
    onINP(handler);
  }
};

export { reportWebVitals, createWebVitalsHandler };