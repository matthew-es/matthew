import * as Sentry from "@sentry/react";

// Environment-specific Sentry configuration
export const getSentryConfig = (): Sentry.BrowserOptions => {
  const isDev = import.meta.env.DEV;
  
  return {
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
    
    // Performance monitoring - 100% dev, 10% prod
    tracesSampleRate: isDev ? 1.0 : 0.1,
    
    // Session replay - 100% dev, 1% prod + always capture errors
    replaysSessionSampleRate: isDev ? 0.0 : 0.01,
    replaysOnErrorSampleRate: isDev ? 0.0: 1.0, // Always capture error sessions
    
    // Integrations will be set by calling code
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        // Privacy-first approach
        maskAllText: !isDev,        // Mask in production, visible in dev
        maskAllInputs: !isDev,      // Mask form inputs in production
        blockAllMedia: !isDev,      // Block images/media in production
      }),
    ],
    
    // Filter noisy errors in production
    beforeSend: (event) => {
      if (!isDev) {
        // Filter common browser extension errors
        const errorMessage = event.exception?.values?.[0]?.value || '';
        
        if (
          errorMessage.includes('ResizeObserver') ||
          errorMessage.includes('Script error') ||
          errorMessage.includes('Non-Error promise rejection') ||
          errorMessage.includes('Loading chunk')
        ) {
          return null; // Don't send these to Sentry
        }
      }
      
      return event;
    },
    
    // Clean up breadcrumbs
    beforeBreadcrumb: (breadcrumb) => {
      // In production, filter out verbose console logs
      if (!isDev && breadcrumb.category === 'console' && breadcrumb.level === 'log') {
        return null;
      }
      
      // Always keep error and warning breadcrumbs
      if (breadcrumb.level === 'error' || breadcrumb.level === 'warning') {
        return breadcrumb;
      }
      
      // Keep navigation breadcrumbs
      if (breadcrumb.category === 'navigation') {
        return breadcrumb;
      }
      
      return breadcrumb;
    }
  };
};

// Initialize Sentry with validation and logging
export const initSentry = () => {
  // Validate required environment variables
  if (!import.meta.env.VITE_SENTRY_DSN) {
    if (import.meta.env.DEV) {
      console.warn('⚠️ VITE_SENTRY_DSN not found - Sentry disabled');
    }
    return false;
  }
  
  const config = getSentryConfig();
  
  try {
    Sentry.init(config);
    
    // Log successful initialization in development
    if (import.meta.env.DEV) {
      console.log('🔍 Sentry initialized:', {
        environment: import.meta.env.MODE,
        dsn: import.meta.env.VITE_SENTRY_DSN?.slice(0, 20) + '...',
        sampling: {
          traces: config.tracesSampleRate,
          normalReplays: config.replaysSessionSampleRate,
          errorReplays: config.replaysOnErrorSampleRate
        },
        privacy: {
          maskText: !import.meta.env.DEV,
          maskInputs: !import.meta.env.DEV,
          blockMedia: !import.meta.env.DEV
        }
      });
    }
    
    return true;
  } catch (error) {
    if (import.meta.env.DEV) {
      console.error('❌ Failed to initialize Sentry:', error);
    }
    return false;
  }
};

// Utility to check if Sentry is properly configured
export const isSentryEnabled = (): boolean => {
  return !!import.meta.env.VITE_SENTRY_DSN && !!Sentry.getCurrentHub().getClient();
};

// Get current Sentry configuration info (for debugging)
export const getSentryInfo = () => {
  if (!isSentryEnabled()) {
    return { enabled: false };
  }
  
  const config = getSentryConfig();
  return {
    enabled: true,
    environment: import.meta.env.MODE,
    isDev: import.meta.env.DEV,
    sampling: {
      traces: config.tracesSampleRate,
      normalReplays: config.replaysSessionSampleRate,
      errorReplays: config.replaysOnErrorSampleRate
    }
  };
};