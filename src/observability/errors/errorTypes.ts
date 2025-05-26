//////////////////////////////////////////////////////////////////////
// 1.0 Error Types with Sentry Integration
//////////////////////////////////////////////////////////////////////

export class FrontError extends Error {
  constructor(
    public userMessage: string,     // What users see
    public userAction: string,      // What users should do
    public logMessage: string,      // What devs see in Sentry
    public context: {               // Extra context for debugging
      component?: string,           // Where it happened
      errorCode?: string,           // Type of error
      statusCode?: number,          // HTTP status if applicable
      timestamp?: string,           // When it happened
      data?: any,                   // Any relevant data
      severity?: 'low' | 'medium' | 'high' | 'critical'
    },
    public cause?: Error            // Original error if any
  ) {
    super(logMessage);
    this.name = 'FrontError';
    this.context.timestamp = this.context.timestamp || new Date().toISOString();
  }

  // Enhanced JSON serialization for Sentry
  toJSON() {
    return {
      name: this.name,
      component: this.context.component,
      userMessage: this.userMessage,
      userAction: this.userAction,
      technical: {
        message: this.logMessage,
        errorCode: this.context.errorCode,
        statusCode: this.context.statusCode,
        timestamp: this.context.timestamp,
        severity: this.context.severity,
        stack: this.stack,
        cause: this.cause
      },
      data: this.context.data
    };
  }

  // Automatically log to Sentry with proper context
  // logToSentry() {
  //   captureError(this, {
  //     component: this.context.component,
  //     extra: {
  //       userMessage: this.userMessage,
  //       userAction: this.userAction,
  //       errorCode: this.context.errorCode,
  //       statusCode: this.context.statusCode,
  //       severity: this.context.severity
  //     }
  //   });
  // }

  // Convenience method to log and return (for easy chaining)
  log() {
    // this.logToSentry();
    
    // Also log to console in development
    if (import.meta.env.DEV) {
      console.error('FrontError:', this.toJSON());
    }
    
    return this;
  }
}

// Helper to convert unknown errors to FrontError
export const wrapError = (
  error: unknown,
  component: string,
  userMessage = "Something went wrong",
  userAction = "Please try again or contact support"
): FrontError => {
  if (error instanceof FrontError) {
    // Already a FrontError, just update component if needed
    if (!error.context.component) {
      error.context.component = component;
    }
    return error;
  }

  const originalError = error instanceof Error ? error : new Error(String(error));
  
  return new FrontError(
    userMessage,
    userAction,
    originalError.message,
    {
      component,
      errorCode: 'WRAPPED_ERROR',
      severity: 'medium',
      data: { originalError: String(error) }
    },
    originalError
  );
};

// Error severity helpers
export const createCriticalError = (
  message: string,
  component: string,
  userMessage?: string,
  cause?: Error
) => new FrontError(
  userMessage || "A critical error occurred",
  "Please refresh the page or contact support immediately",
  message,
  { component, errorCode: 'CRITICAL', severity: 'critical' },
  cause
);

export const createUserError = (
  userMessage: string,
  userAction: string,
  component: string,
  technical?: string
) => new FrontError(
  userMessage,
  userAction,
  technical || userMessage,
  { component, errorCode: 'USER_ERROR', severity: 'low' }
);

export const createApiError = (
  statusCode: number,
  component: string,
  apiMessage?: string
) => {
  const getMessage = (code: number) => {
    switch (code) {
      case 401: return "You need to log in to continue";
      case 403: return "You don't have permission to do that";
      case 404: return "The requested resource was not found";
      case 500: return "Server error - we're looking into it";
      default: return "Something went wrong with the request";
    }
  };

  return new FrontError(
    getMessage(statusCode),
    "Please try again or contact support if the problem persists",
    apiMessage || `API Error ${statusCode}`,
    { 
      component, 
      errorCode: 'API_ERROR', 
      statusCode, 
      severity: statusCode >= 500 ? 'high' : 'medium' 
    }
  );
};

export interface FrontErrorProps {
  error: FrontError;
}