import log from 'loglevel';

// Set the default log level based on environment
// In production, we might want to show fewer logs
const defaultLevel = import.meta.env.PROD ? log.levels.ERROR : log.levels.DEBUG;
log.setLevel(defaultLevel);

// Enable log persistence to localStorage if needed
// This allows us to see logs even after page refresh
const persistLogs = false;
if (persistLogs) {
    const originalFactory = log.methodFactory;
    log.methodFactory = function (methodName, logLevel, loggerName) {
        const rawMethod = originalFactory(methodName, logLevel, loggerName);

        return function (...args) {
            rawMethod(...args);
            try {
                const logs = JSON.parse(localStorage.getItem('app_logs') || '[]');
                logs.push({
                    timestamp: new Date().toISOString(),
                    level: methodName,
                    args: args.map(arg =>
                        arg instanceof Error
                            ? { name: arg.name, message: arg.message, stack: arg.stack }
                            : arg
                    )
                });
                // Keep only the last 100 logs to avoid localStorage overflow
                if (logs.length > 100) logs.shift();
                localStorage.setItem('app_logs', JSON.stringify(logs));
            } catch (e) {
                // If localStorage fails, just continue
            }
        };
    };

    // Apply the new factory
    log.setLevel(log.getLevel());
}

// Add support for component context
export function getLogger(context: string) {
    return {
        trace: (...args: unknown[]) => log.trace(`[${context}]`, ...args),
        debug: (...args: unknown[]) => log.debug(`[${context}]`, ...args),
        info: (...args: unknown[]) => log.info(`[${context}]`, ...args),
        warn: (...args: unknown[]) => log.warn(`[${context}]`, ...args),
        error: (...args: unknown[]) => log.error(`[${context}]`, ...args),
    };
}

// Export the raw logger for direct use
export default log;