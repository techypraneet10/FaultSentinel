import {
  AnalyzeRequest,
  AnalyzeResponse,
  HealthLiveResponse,
  HealthReadyResponse,
  RootMetadataResponse,
  ApiErrorResponse,
} from '../types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  code: string;
  requestId: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, code: string, requestId: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.requestId = requestId;
    this.status = status;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  const requestId = res.headers.get('x-request-id') || 'unknown';

  if (!res.ok) {
    let errorCode = 'API_ERROR';
    let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
    let details: Record<string, unknown> | undefined;

    try {
      const errorBody: ApiErrorResponse = await res.json();
      if (errorBody && errorBody.error) {
        errorCode = errorBody.error.code || errorCode;
        errorMessage = errorBody.error.message || errorMessage;
        details = errorBody.error.details;
      }
    } catch {
      // Body was not JSON
    }

    throw new ApiError(errorMessage, errorCode, requestId, res.status, details);
  }

  return res.json() as Promise<T>;
}

export const apiService = {
  async healthLive(signal?: AbortSignal): Promise<HealthLiveResponse> {
    const res = await fetch(`${BASE_URL}/health/live`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<HealthLiveResponse>(res);
  },

  async healthReady(signal?: AbortSignal): Promise<HealthReadyResponse> {
    const res = await fetch(`${BASE_URL}/health/ready`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<HealthReadyResponse>(res);
  },

  async fetchRootMetadata(signal?: AbortSignal): Promise<RootMetadataResponse> {
    const res = await fetch(`${BASE_URL}/api/v1`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<RootMetadataResponse>(res);
  },

  async analyzeLogs(request: AnalyzeRequest, signal?: AbortSignal): Promise<AnalyzeResponse> {
    const res = await fetch(`${BASE_URL}/api/v1/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(request),
      signal,
    });
    return handleResponse<AnalyzeResponse>(res);
  },
};
