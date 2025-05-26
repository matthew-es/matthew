// Main exports for Sentry functionality
export { initSentry, getSentryConfig, isSentryEnabled, getSentryInfo } from './config';

// Re-export Sentry itself for direct access when needed
import * as Sentry from "@sentry/react";
export { Sentry };

// Convenience functions for common Sentry operations
export const captureError = (error: unknown, context?: {
  component?: string;
  user?: any;
  extra?: Record<string, any>;
}) => {
  Sentry.withScope((scope) => {
    if (context?.component) {
      scope.setTag('component', context.component);
    }
    
    if (context?.user) {
      scope.setUser(context.user);
    }
    
    if (context?.extra) {
      scope.setContext('error_context', context.extra);
    }
    
    Sentry.captureException(error);
  });
};

// Simple message capture
export const captureMessage = (message: string, level: 'info' | 'warning' | 'error' = 'info') => {
  Sentry.captureMessage(message, level);
};

// User context management
export const setUserContext = (user: { id: string; email?: string; role?: string }) => {
  Sentry.setUser(user);
};

export const clearUserContext = () => {
  Sentry.setUser(null);
};