// Import everything we need to use in this file
import { 
    FrontError, 
    wrapError, 
    createCriticalError, 
    createUserError, 
    createApiError,
    FrontErrorProps 
  } from './errorTypes';
  
  // Re-export everything for other files to use
  export { FrontError, wrapError, createCriticalError, createUserError, createApiError };
  export type { FrontErrorProps };
  
  // Central error handler that logs and returns FrontError
  export const handleError = (
    error: unknown,
    component: string = 'unknown',
    userMessage?: string,
    userAction?: string
  ): FrontError => {
    const frontError = wrapError(error, component, userMessage, userAction);
    frontError.log(); // Automatically logs to Sentry + console in dev
    return frontError;
  };
  
  // For async operations with automatic error handling
  export const handleAsyncError = async <T>(
    operation: () => Promise<T>,
    component: string,
    userMessage?: string
  ): Promise<T> => {
    try {
      return await operation();
    } catch (error) {
      throw handleError(error, component, userMessage);
    }
  };
  
  // For React error boundaries
  export const convertToFrontError = (error: unknown, component: string = 'ErrorBoundary'): FrontError => {
    return wrapError(error, component, 'The app encountered an unexpected error');
  };