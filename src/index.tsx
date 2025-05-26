import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// import * as obs from "@/observability";
// console.log('Available exports:', Object.keys(obs));

import { initSentry, Sentry, reportWebVitals, convertToFrontError } from "@/observability";

// Initialize Sentry
initSentry();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <Sentry.ErrorBoundary 
      fallback={({ error, resetError }) => {  // ← Remove the explicit type annotation
        const frontError = convertToFrontError(error, 'ErrorBoundary');
        
        return (
          <div className="error-boundary">
            <div className="error-boundary-content">
              <h1 className="text-2xl font-bold text-gray-900 mb-4">Oops! Something went wrong</h1>
              <p className="text-gray-600 mb-2">{frontError.userMessage}</p>
              <p className="text-sm text-gray-500 mb-6">
                <strong>What you can do:</strong> {frontError.userAction}
              </p>
              <button 
                onClick={resetError}
                className="error-boundary-button"
              >
                Try again
              </button>
            </div>
          </div>
        );
      }}
    >
      <App />
    </Sentry.ErrorBoundary>
  </React.StrictMode>
);

reportWebVitals();