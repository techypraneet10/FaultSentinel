import {
  AnalyzeRequest,
  AnalyzeResponse,
  HealthLiveResponse,
  HealthReadyResponse,
  RootMetadataResponse,
  ApiErrorResponse,
  DiagnosticsResponse,
  ObservabilityHealthResponse,
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

  async fetchDiagnostics(signal?: AbortSignal): Promise<DiagnosticsResponse> {
    const res = await fetch(`${BASE_URL}/api/v1/diagnostics`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<DiagnosticsResponse>(res);
  },

  async healthObservability(signal?: AbortSignal): Promise<ObservabilityHealthResponse> {
    const res = await fetch(`${BASE_URL}/health/observability`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<ObservabilityHealthResponse>(res);
  },

  /* v1.1 Workbench APIs */
  async fetchIncidentReplay(incidentId: string, dataset: string = 'hdfs', signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/replay/${encodeURIComponent(incidentId)}?dataset=${dataset}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<any>(res);
  },

  async fetchSampleReplay(scenarioType: string = 'incident', dataset: string = 'hdfs', signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/replay/sample/${encodeURIComponent(scenarioType)}?dataset=${dataset}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<any>(res);
  },

  async simulateCounterfactual(payload: any, signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents/counterfactual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
    return handleResponse<any>(res);
  },

  async listFaultScenarios(signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/fault-injection/scenarios`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<any>(res);
  },

  async runFaultScenario(scenarioId: string, environment: string = 'local', signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/fault-injection/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId, environment }),
      signal,
    });
    return handleResponse<any>(res);
  },

  async evaluateCalibrationDrift(dataset: string = 'hdfs', simulateDrift: boolean = false, signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/calibration/drift?dataset=${dataset}&simulate_drift=${simulateDrift}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<any>(res);
  },

  async fetchEvidenceGraph(incidentId: string, dataset: string = 'hdfs', signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/evidence/${encodeURIComponent(incidentId)}/graph?dataset=${dataset}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<any>(res);
  },

  async fetchDecisionPassport(incidentId: string, dataset: string = 'hdfs', signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents/${encodeURIComponent(incidentId)}/passport?dataset=${dataset}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<any>(res);
  },

  async verifyDecisionPassport(incidentId: string, passport: any, signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents/${encodeURIComponent(incidentId)}/passport/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ passport }),
      signal,
    });
    return handleResponse<any>(res);
  },

  async submitHumanReview(incidentId: string, review: any, signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents/${encodeURIComponent(incidentId)}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(review),
      signal,
    });
    return handleResponse<any>(res);
  },

  async fetchHumanReviewsSummary(signal?: AbortSignal): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents/reviews/summary`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    return handleResponse<any>(res);
  },
};
