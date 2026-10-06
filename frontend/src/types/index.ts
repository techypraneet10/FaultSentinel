/**
 * Core TypeScript types for SentinelLog Operator Dashboard.
 * Strictly synchronized with Phase 10 API contracts in sentinellog/serving/api/schemas.py.
 */

export type DatasetType = 'hdfs' | 'bgl';

export type DecisionType = 'INCIDENT' | 'SUSPICIOUS' | 'INSUFFICIENT_EVIDENCE';

export type SeverityType = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';

export type AnalysisStatus = 'success' | 'abstention' | 'error';

export type ExplanationStatus = 'GENERATED' | 'SKIPPED' | 'FAILED';

export type EvidenceSufficiencyStatus = 'SUFFICIENT' | 'INSUFFICIENT';

export type ProvenanceStatus = 'VERIFIED' | 'REJECTED';

export type FaithfulnessStatus = 'VERIFIED' | 'UNFAITHFUL';

export type ClaimType =
  | 'OBSERVATION'
  | 'EVIDENCE'
  | 'CORRELATION'
  | 'INTERPRETATION'
  | 'UNCERTAINTY'
  | 'RECOMMENDATION';

export interface AnalysisOptions {
  window_id?: string | null;
  include_citations?: boolean;
  include_raw_excerpts?: boolean;
}

export interface AnalyzeRequest {
  dataset: DatasetType;
  logs: string[];
  options?: AnalysisOptions | null;
}

export interface Claim {
  claim_id: string;
  claim_type: string;
  text: string;
  citation_ids: string[];
  supported: boolean;
  support_score: number;
}

export interface Citation {
  citation_id: string;
  dataset: string;
  split: string;
  source_window_id: string;
  line_start?: number | null;
  line_end?: number | null;
  citation_text?: string | null;
}

export interface ProcessingMetadata {
  record_count?: number;
  model_name?: string;
  provider?: string;
  [key: string]: unknown;
}

export interface AnalyzeResponse {
  request_id: string;
  status: AnalysisStatus;
  dataset: string;
  decision: DecisionType;
  severity: SeverityType;
  confidence: number;
  explanation_status: ExplanationStatus;
  summary?: string | null;
  explanation?: string | null;
  claims: Claim[];
  citations: Citation[];
  evidence_sufficiency: EvidenceSufficiencyStatus;
  provenance_status: ProvenanceStatus;
  faithfulness_status: FaithfulnessStatus;
  processing_metadata: ProcessingMetadata;
}

export interface HealthLiveResponse {
  status: string;
}

export interface HealthReadyResponse {
  status: 'ready' | 'not_ready' | string;
  checks: Record<string, string>;
}

export interface RootMetadataResponse {
  service_name: string;
  api_version: string;
  app_version: string;
  status: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  request_id: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export type ConnectionState = 'connected' | 'degraded' | 'offline' | 'checking';
