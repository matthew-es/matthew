# Error Handling System

## Purpose
This folder provides a comprehensive, type-safe error handling system integrated with Sentry for monitoring and debugging across the entire application.

## Goals
- **Consistent Error Handling**: Standardized error creation and management throughout the app
- **User-Friendly Messages**: Clear, actionable messages for end users
- **Developer Context**: Rich technical details for debugging and monitoring
- **Sentry Integration**: Automatic error reporting with structured context
- **Type Safety**: Full TypeScript support for error handling workflows
- **Severity Classification**: Categorize errors by impact and urgency level

## Files & Responsibilities

### `errorTypes.ts`
**Purpose**: Core error classes and specialized error creation helpers

**Key Exports**:
- `FrontError`: Main error class with dual user/technical messaging
- `wrapError()`: Convert any unknown error into a FrontError
- `createCriticalError()`: High-severity system failures
- `createUserError()`: Low-severity user input validation errors  
- `createApiError()`: Network/API errors with HTTP status codes
- `FrontErrorProps`: TypeScript interface for error props

**FrontError Class Features**:
- **Dual messaging**: Separate user-friendly and technical messages
- **Rich context**: Component source, error codes, timestamps, custom data
- **Automatic logging**: Built-in Sentry integration via `.log()` method
- **Severity levels**: `critical | high | medium | low`
- **Error chaining**: Preserve original error as `cause`
- **JSON serialization**: Structured output for logging and debugging

### `index.ts`
**Purpose**: Main export point and high-level error handling utilities

**Key Exports**:
- `handleError()`: Central error processor with automatic logging
- `handleAsyncError()`: Wrapper for async operations with error handling
- `convertToFrontError()`: Specialized converter for React error boundaries
- Re-exports all error types and creation helpers from errorTypes.ts

**Error Handling Utilities**:
- **handleError()**: Converts any error + logs to Sentry + returns FrontError
- **handleAsyncError()**: Wraps async functions with automatic error handling
- **convertToFrontError()**: For React error boundaries and component crashes

## Error Structure & API

### FrontError Constructor

```typescript
new FrontError(
  userMessage: string,        // What users see: "Failed to save your changes"
  userAction: string,         // What users should do: "Please try again"
  logMessage: string,         // Technical details: "API timeout after 30s"
  context: {
    component?: string,       // "UserProfile", "LoginForm", etc.
    errorCode?: string,       // "API_TIMEOUT", "VALIDATION_ERROR", etc.
    statusCode?: number,      // HTTP status: 404, 500, etc.
    timestamp?: string,       // Auto-generated ISO timestamp
    data?: any,              // Additional debug context
    severity?: 'low' | 'medium' | 'high' | 'critical'
  },
  cause?: Error              // Original error if wrapping existing error
)
```

#### FrontError Methods

.log(): Send to Sentry + console log in dev, returns self for chaining
.logToSentry(): Send to Sentry only with structured context
.toJSON(): Serialize for logging with user/technical separation

#### Severity Classification

Critical
- System crashes, data corruption, security breaches
- Examples: Database failures, authentication system down
- User impact: Complete feature failure
- Response: Immediate escalation required

High
- Major feature breaks, API failures, payment processing issues
- Examples: Login broken, API returning 500s, checkout failing
- User impact: Core functionality unavailable
- Response: Fix within hours

Medium
- Validation errors, network timeouts, non-critical API failures
- Examples: Form validation, slow API response, 404 errors
- User impact: Workflow interrupted but workarounds exist
- Response: Fix within days

Low
- User input errors, warnings, informational messages
- Examples: Invalid email format, missing required field
- User impact: Guided correction needed
- Response: User education or UX improvement

#### Helper Functions

Error Creation Helpers:
```typescript
// Critical system errors
createCriticalError(
  "Database connection failed",     // Technical message
  "UserService",                   // Component
  "Service temporarily unavailable" // User message (optional)
)

// User validation errors  
createUserError(
  "Please enter a valid email address",  // User message
  "Check your email and try again",      // User action
  "LoginForm",                           // Component
  "Email validation failed: invalid@"    // Technical details (optional)
)

// API/Network errors
createApiError(
  404,              // HTTP status code
  "UserAPI",        // Component
  "User not found"  // API message (optional)
)
```

Error Handling Utilities:
```typescript
// Basic error handling with auto-logging
const frontError = handleError(
  error,                    // Any error type
  'ComponentName',          // Where it happened
  'Custom user message',    // Optional override
  'Custom user action'      // Optional override
)

// Async operation wrapper
const result = await handleAsyncError(
  () => api.fetchUser(id),  // Async operation
  'UserProfile',            // Component context
  'Failed to load profile'  // User message
)

// For React error boundaries
const boundaryError = convertToFrontError(
  error,           // React error
  'ErrorBoundary'  // Component (optional)
)
```

#### Integration Points

Sentry Integration
- All FrontErrors automatically send structured data to Sentry
- Component tags for filtering and grouping
- Severity levels for alert prioritization
- User context and custom data preservation
- Environment separation (dev vs production)

React Error Boundaries
- `convertToFrontError()` standardizes boundary error handling
- Graceful fallback UI with user-friendly messaging
- Automatic Sentry reporting of component crashes

API Error Handling
- `createApiError()` provides standardized HTTP error responses
- Status code mapping to user-friendly messages
- Network timeout and connectivity error handling

Form Validation
- `createUserError()` for input validation feedback
- Low severity classification for user guidance
- Clear user action instructions

### Usage Examples

Component Error Handling:
```typescript
import { handleError, createUserError } from '@/observability/errors';

const UserProfile = () => {
  const updateProfile = async (data) => {
    try {
      await api.updateUser(data);
    } catch (error) {
      const frontError = handleError(
        error,
        'UserProfile',
        'Failed to update your profile'
      );
      
      // Error automatically logged to Sentry
      setErrorMessage(frontError.userMessage);
      setErrorAction(frontError.userAction);
    }
  };
};
```

API Service Integration:
```typescript
import { createApiError, handleAsyncError } from '@/observability/errors';

class UserService {
  async getUser(id: string) {
    return handleAsyncError(
      async () => {
        const response = await fetch(`/api/users/${id}`);
        if (!response.ok) {
          throw createApiError(response.status, 'UserService');
        }
        return response.json();
      },
      'UserService',
      'Failed to load user information'
    );
  }
}
```

Form Validation:
```typescript
import { createUserError } from '@/observability/errors';

const validateEmail = (email: string) => {
  if (!email.includes('@')) {
    throw createUserError(
      'Please enter a valid email address',
      'Make sure your email includes an @ symbol',
      'EmailValidation',
      `Invalid email format: ${email}`
    ).log(); // Send to Sentry for UX improvement tracking
  }
};
```

#### Success Criteria

- All application errors flow through FrontError system
- Automatic Sentry integration capturing structured error data
- User-friendly error messages displayed consistently
- Rich debugging context available for all errors
- Error severity properly classified and routed
- TypeScript compilation errors eliminated
- React error boundaries using standardized error handling
- API errors providing actionable user guidance
- Development vs production error handling optimized