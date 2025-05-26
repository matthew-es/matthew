# Monitoring Description

## Purpose
This folder handles all client-side performance monitoring, web vitals collection, and performance-related telemetry that gets sent to our observability stack (primarily Sentry).

## Goals
- **Automated Performance Tracking**: Collect Core Web Vitals automatically without manual instrumentation
- **Dual Logging Strategy**: Send ALL telemetry to Sentry (dev + prod), PLUS console logging in dev for immediate feedback
- **Performance Alerting**: Flag poor performance metrics for investigation
- **Manual Instrumentation**: Provide utilities for custom performance tracking
- **Cost-Effective**: Smart sampling and filtering to control Sentry costs

## Files & Responsibilities

### `report-web-vitals.ts`
**Purpose**: Automated collection of Core Web Vitals (LCP, INP, CLS, FCP, TTFB)

**Key Functions**:
- `createWebVitalsHandler()`: Creates handler that ALWAYS sends to Sentry + console logs in dev
- `getMetricUnit()`: Maps metric names to correct units (ms, unitless, etc.)
- `reportWebVitals()`: Subscribes to all web vital events

**Data Flow**:
1. Web vitals fire automatically during user interaction
2. Handler receives metric with value, rating (good/needs-improvement/poor)
3. **Always**: Send to Sentry as measurements + breadcrumbs (tagged with environment)
4. **Dev only**: Also log to console for immediate debugging
5. Poor ratings trigger warning messages in Sentry

### `index.ts`
**Purpose**: Main export point + manual performance utilities

**Key Exports**:
- `reportWebVitals`: Main function to start automated monitoring
- `performanceMonitoring`: Utilities for manual performance tracking
  - `mark()`: Set performance marks
  - `measure()`: Measure between marks  
  - `getEntries()`: Retrieve performance data

## Integration Points
- **Sentry**: ALL metrics flow to Sentry in both dev and production (environment tagged)
- **index.tsx**: Called once at app startup to begin monitoring
- **Components**: Can use manual utilities for specific performance tracking

## Performance Considerations
- **Zero Runtime Cost**: Web vitals are collected by browser APIs, minimal JS overhead
- **Environment Separation**: Dev and prod data tagged separately in Sentry
- **Sampling**: Production metrics are sampled to control Sentry costs

## Metrics Collected

### Core Web Vitals (affect SEO)
- **LCP (Largest Contentful Paint)**: Main content load time - target <2.5s
- **INP (Interaction to Next Paint)**: Responsiveness - target <200ms  
- **CLS (Cumulative Layout Shift)**: Visual stability - target <0.1

### Additional Metrics
- **FCP (First Contentful Paint)**: When anything first appears
- **TTFB (Time to First Byte)**: Server response time

## Usage Examples

```typescript
// Automatic monitoring (in index.tsx)
import { reportWebVitals  } from '@/observability';
reportWebVitals(); // Starts automatic collection

// Manual performance tracking
import { performanceMonitoring } from '@/observability';

// Time an API call example
performanceMonitoring.mark('api-start');
await fetchData();
performanceMonitoring.mark('api-end');
performanceMonitoring.measure('api-duration', 'api-start', 'api-end');