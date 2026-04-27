import * as Sentry from '@sentry/react-native';
import ENV from '@/constants/config';

let initialized = false;

export function initSentry(): void {
  if (initialized || !ENV.SENTRY_DSN) return;

  Sentry.init({
    dsn: ENV.SENTRY_DSN,
    tracesSampleRate: __DEV__ ? 1.0 : 0.2,
    enableAutoSessionTracking: true,
    sessionTrackingIntervalMillis: 30000,
    attachStacktrace: true,
    environment: __DEV__ ? 'development' : 'production',
  });

  initialized = true;
}

export function captureError(error: unknown, context?: Record<string, unknown>): void {
  if (context) {
    Sentry.setContext('extra', context);
  }
  if (error instanceof Error) {
    Sentry.captureException(error);
  } else {
    Sentry.captureMessage(String(error));
  }
}

export function setUser(id: number | null, email?: string): void {
  if (id) {
    Sentry.setUser({ id: String(id), email });
  } else {
    Sentry.setUser(null);
  }
}
