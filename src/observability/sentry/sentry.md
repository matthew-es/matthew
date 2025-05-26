# Sentry Integration

## Purpose
This folder manages all Sentry configuration, initialization, and custom integrations for error tracking, performance monitoring, and session replay across development and production environments.

## Goals
- **Environment-Aware Configuration**: Different settings for dev vs production
- **Cost-Effective Sampling**: Smart sampling rates to control Sentry costs
- **Privacy-First**: Mask sensitive data while preserving debugging capability
- **Rich Context**: Capture meaningful error context and user sessions
- **Performance Monitoring**: Track real user performance metrics
- **Easy Integration**: Simple imports throughout the app

## Files & Responsibilities

### `config.ts`
**Purpose**: Core Sentry configuration and initialization

**Key Functions**:
- `getSentryConfig()`: Returns environment-specific Sentry configuration
- `initSentry()`: Initializes Sentry with proper settings
- Environment detection and sampling rate management
- Privacy settings (masking/blocking) configuration

**Configuration Strategy**:
- **Development**: Full sampling (1.0), full debugging, console + Sentry
- **Production**: Conservative sampling (0.01-0.1), privacy masking, Sentry only

### `index.ts`
**Purpose**: Main export point and convenience functions

**Key Exports**:
- `initSentry`: Main initialization function
- `captureError`: Enhanced error capture with context
- `captureMessage`: Enhanced message logging
- `setUserContext`: User identification for debugging
- Sentry configuration utilities

## Integration Points
- **index.tsx**: Called once at app startup for initialization
- **Error boundaries**: Uses Sentry.ErrorBoundary component
- **Error handling**: All errors flow through Sentry capture
- **Performance monitoring**: Web vitals and custom metrics

## Privacy & Security
- **Data Masking**: All form inputs and sensitive text masked in production
- **Media Blocking**: Profile pictures and uploads blocked in production
- **Selective Unmasking**: [future] Public content can be unmasked via data attributes
- **Environment Separation**: Dev and production data clearly separated

## Sampling Strategy

### Development
- **Traces**: 100% (tracesSampleRate: 1.0)
- **Session Replays**: 100% normal + 100% errors (replaysSessionSampleRate: 1.0)
- **Rationale**: Full visibility for debugging

### Production  
- **Traces**: 10% (tracesSampleRate: 0.1)
- **Session Replays**: 1% normal + 100% errors (replaysSessionSampleRate: 0.01)
- **Rationale**: Representative data without excessive costs

## Cost Management
- **Replay Limits**: Stay under 5K replays/month (~$44/month plan)
- **Smart Filtering**: Filter out noisy/irrelevant events
- **Error-First**: Always capture errors, sample normal sessions
- **Performance Alerts**: Monitor approaching quota limits

## Usage Examples

```typescript
// App initialization (index.tsx)
import { initSentry } from '@/observability/sentry';
initSentry();

// Error handling in components
import { captureError, setUserContext } from '@/observability/sentry';

// Capture custom errors
try {
  await riskyOperation();
} catch (error) {
  captureError(error, {
    component: 'UserProfile',
    context: { userId: user.id, action: 'updateProfile' }
  });
}

// Set user context for debugging
setUserContext({
  id: user.id,
  email: user.email, // This will be masked in production replays
  role: user.role
});