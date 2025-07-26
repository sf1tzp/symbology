import log from 'loglevel';
import { config } from './config';

// Set the default log level based on environment
// In production, we might want to show fewer logs
const defaultLevel = import.meta.env.PROD ? log.levels.ERROR : log.levels.DEBUG;
log.setLevel(defaultLevel);

// Configuration options for logger
interface LoggerConfig {
  sendToBackend?: boolean;
  backendLevels?: string[];
  extraData?: Record<string, any>;
}

// Function to send logs to backend
async function sendLogToBackend(logEntry: any) {
  try {
    await fetch(`${config.api.baseUrl}/logs/log`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_agent: navigator.userAgent,
        url: window.location.href,
        timestamp: logEntry['timestamp'],
        level: logEntry['level'],
        component: logEntry['component'],
        event: logEntry['event'],
        args: logEntry['args'],
        // ...logEntry[1],
      }),
    });
  } catch (err) {
    log.debug('Could not make the request');
    // Don't log this error to avoid infinite loops
  }
}

// Global error handler for unhandled errors
window.addEventListener('error', (event) => {
  log.error('Unhandled error:', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error,
  });
});

// Global handler for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  log.error('Unhandled promise rejection:', {
    reason: event.reason,
    promise: event.promise,
  });
});

export function getLogger(context: string, config: LoggerConfig = {}) {
  return {
    trace: (...args: unknown[]) => log.trace(`[${context}]`, ...args),
    debug: (...args: unknown[]) => log.debug(`[${context}]`, ...args),
    info: (...args: unknown[]) => log.info(`[${context}]`, ...args),
    warn: (...args: unknown[]) => log.warn(`[${context}]`, ...args),
    error: (...args: unknown[]) => log.error(`[${context}]`, ...args),
  };
}

export function getComponentLogger(component: string) {
  // Check if we should send logs based on environment
  const environment = config.env;
  const isDev = environment === 'development' || environment === 'dev';
  const isStaging = environment === 'staging';

  const shouldSendLogs = true || isDev || isStaging;

  console.log(`setup_component_logger`, {
    component,
    environment,
    isDev,
    isStaging,
    shouldSendLogs,
  });

  if (shouldSendLogs) {
    return createBackendLogger(component);
  } else {
    return getLogger(component);
  }

  // Internal function to create loggers with backend integration
  function createBackendLogger(component: string) {
    const sendLog = (level: string, ...args: unknown[]) => {
      const logEntry = {
        timestamp: new Date().toISOString(),
        component: component,
        level: level,
        event: args[0],
        args: args[1],
      };

      sendLogToBackend(logEntry).catch(() => {
        // Silently fail - don't want logging to break the app
      });
    };

    return {
      trace: (...args: unknown[]) => {
        log.trace(`[${component}]`, ...args);
        sendLog('trace', ...args);
      },
      debug: (...args: unknown[]) => {
        log.debug(`[${component}]`, ...args);
        sendLog('debug', ...args);
      },
      info: (...args: unknown[]) => {
        log.info(`[${component}]`, ...args);
        sendLog('info', ...args);
      },
      warn: (...args: unknown[]) => {
        log.warn(`[${component}]`, ...args);
        sendLog('warn', ...args);
      },
      error: (...args: unknown[]) => {
        log.error(`[${component}]`, ...args);
        sendLog('error', ...args);
      },
    };
  }
}

// Export the raw logger for direct use
export default log;
