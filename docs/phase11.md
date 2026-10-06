# SentinelLog Phase 11 — Operator Dashboard & Human Review Interface

## 1. Objective
Phase 11 provides the human-facing operational review interface for SentinelLog. Built directly over the Phase 10 REST API (`POST /api/v1/analyze`, `GET /health/live`, `GET /health/ready`, `GET /api/v1`), it allows site reliability engineers (SREs) and security operations center (SOC) analysts to submit bounded system log sequences, observe calibrated triage decisions, review grounded incident explanations, audit claim-to-citation mappings, and inspect source evidence coordinates without altering the underlying research pipeline.

The operator dashboard is an **interface of presentation, navigation, and human verification**. It does not perform anomaly scoring, selective prediction gating, retrieval, evidence reranking, deterministic reasoning, or LLM generation.

---

## 2. UI Architecture
The dashboard is strictly downstream of the Phase 10 serving API:

```
Operator / Reviewer
       ↓
Phase 11 React Operator Dashboard
       ↓
apiService (HTTP fetch)
       ↓
Phase 10 FastAPI Serving Layer (/api/v1/analyze)
       ↓
AnalysisService / PipelineService
       ↓
Drain Log Parsing
       ↓
Phase 4 Conformal Selective Gating (α=0.05)
       ↓
Phase 5 Semantic Retrieval
       ↓
Phase 6 Deterministic MMR Reranking
       ↓
Phase 7 Provenance Engine (Precision=1.0, Coverage=1.0)
       ↓
Phase 8 Deterministic Reasoning Engine (Authoritative Decision)
       ↓
Phase 9 Grounded LLM Explanation Orchestrator
       ↓
Phase 10 JSON Response (AnalyzeResponse)
       ↓
Phase 11 Dashboard Rendering
```

---

## 3. Frontend Stack
- **Framework**: React 18.3.1 (TypeScript 5.5)
- **Bundler / Dev Server**: Vite 5.4.1
- **Icons**: Lucide React 1.16.0
- **Testing**: Vitest 2.1.9, React Testing Library 16.0.0, jsdom 24.1.1
- **Linting**: ESLint 9.9.0 with TypeScript-ESLint flat config
- **Styling**: Vanilla CSS with strict design tokens (`tokens.css` and `index.css`), optimized for dark, high-contrast, technical SRE environments. Zero heavyweight UI frameworks.

---

## 4. Pages & Routes
1. **Incident Analysis (`AnalyzePage`)**:
   - Log ingestion workspace with bounded editor (max 200 lines, 2,000 chars/line, 1 MB payload).
   - Dataset selector (`HDFS`, `BGL`).
   - Demo log loaders with explicit `DEMO / SAMPLE` badges.
   - Analysis execution button with indeterminate progress state.
   - Triage decision card, evidence governance badges, grounded explanation panel, and claim list with type filtering.
2. **Evidence Review (`ReviewPage`)**:
   - Dedicated citation audit table showing citation IDs, datasets, splits, source window IDs, and relative line ranges.
   - Inspection triggers opening the source evidence drawer.
3. **API Status (`ApiStatusPage`)**:
   - Inspects real health probes (`/health/live`, `/health/ready`) and `/api/v1` metadata.
   - Displays granular subsystem dependency states (`configuration`, `pipeline`).
4. **Architecture Overview (`OverviewPage`)**:
   - Architectural documentation detailing the processing hierarchy, Phase 8 decision authority, and BGL calibration safety.

---

## 5. Component Inventory
| Component | Responsibility |
|---|---|
| `Header` | Application branding, navigation tabs, and live API connection indicator |
| `HealthIndicator` | Live/Degraded/Offline indicator polling Phase 10 health probes |
| `StatusBadge` | Semantic status badges (`VERIFIED`, `REJECTED`, `SUFFICIENT`, etc.) |
| `SeverityBadge` | Technical severity badges (`HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`) |
| `DecisionCard` | Authoritative Phase 8 incident decision banner with engine attribution |
| `EvidenceStatus` | Verification panels for Evidence Sufficiency, Provenance, and Faithfulness |
| `ExplanationPanel` | Safe markdown rendering of Phase 9 explanations with summary and statuses |
| `ClaimCard` | Structured claim card displaying claim type, support status, and citation buttons |
| `CitationBadge` | Clickable citation badge linking claim statements to source evidence |
| `EvidenceDrawer` | Sliding side panel displaying source window metadata and bounded excerpts |
| `RequestIdDisplay` | Tracing ID display with copy-to-clipboard functionality |
| `LogEditor` | Bounded multi-line log editor with live record counter, payload telemetry, and demo loaders |
| `ProcessingMetadata` | Collapsible telemetry drawer displaying parsed records and provider details |
| `EmptyState` | Informative onboarding prompt when no analysis has been executed |
| `LoadingState` | Indeterminate progress spinner preventing duplicate requests |
| `ErrorState` | Sanitized error banner displaying backend error code and request ID |

---

## 6. API Integration
All backend network communications are centralized in [`frontend/src/services/api.ts`](file:///d:/FaultSentinel/frontend/src/services/api.ts):
- `healthLive()`: Calls `GET /health/live`.
- `healthReady()`: Calls `GET /health/ready`.
- `fetchRootMetadata()`: Calls `GET /api/v1`.
- `analyzeLogs(request)`: Calls `POST /api/v1/analyze`.

The API client normalizes error payloads into `ApiError` instances containing `code`, `message`, `requestId`, and `status`.

---

## 7. Request & Response Types
Types in [`frontend/src/types/index.ts`](file:///d:/FaultSentinel/frontend/src/types/index.ts) strictly match Phase 10 backend Pydantic models:
- `AnalyzeRequest`: `{ dataset: 'hdfs' | 'bgl', logs: string[], options?: AnalysisOptions }`
- `AnalyzeResponse`: `{ request_id, status, dataset, decision, severity, confidence, explanation_status, summary, explanation, claims, citations, evidence_sufficiency, provenance_status, faithfulness_status, processing_metadata }`
- `Claim`: `{ claim_id, claim_type, text, citation_ids, supported, support_score }`
- `Citation`: `{ citation_id, dataset, split, source_window_id, line_start, line_end, citation_text }`

---

## 8. Decision Semantics
- **Authoritative Authority**: All triage decisions (`INCIDENT`, `SUSPICIOUS`, `INSUFFICIENT_EVIDENCE`) and severities originate exclusively from Phase 8 deterministic reasoning.
- **Explanatory Attribution**: The UI explicitly states: *"Decision generated by the deterministic reasoning engine."*
- **Subordination of LLM**: The LLM explanation is presented as grounded commentary, never as the decision maker.

---

## 9. Evidence & Provenance Workflow
- **Evidence Sufficiency**: Evaluates whether the log sequence contains sufficient density for triage (`SUFFICIENT` vs. `INSUFFICIENT`).
- **Source Provenance**: Validates that all citations trace back to Phase 7 lineage (`VERIFIED` vs. `REJECTED`). If rejected, a prominent warning alerts the operator that citations cannot be trusted.
- **Faithfulness Status**: Validates that explanation statements are backed by cited evidence (`VERIFIED` vs. `UNFAITHFUL`). If unfaithful, alerts the operator: *"Grounding verification failed"*.

---

## 10. Citation Workflow
1. Operator reviews explanation text and extracted claims.
2. Each factual claim displays supporting citation tags (e.g. `[CIT-HDFS-001]`).
3. Clicking a citation badge opens the `EvidenceDrawer`.
4. The drawer displays dataset, split, source window identifier, line ranges, and bounded excerpts.
5. Operators can cross-examine the claim against historical incident evidence.

---

## 11. Security & Protection
- **Zero HTML Injection**: Markdown rendering uses [`SafeMarkdown`](file:///d:/FaultSentinel/frontend/src/utils/markdown.tsx), which constructs React JSX elements directly from parsed markdown tokens. Zero use of `dangerouslySetInnerHTML`.
- **Log Isolation**: System logs are treated as untrusted text DATA. Script tags and HTML elements are rendered as literal text.
- **Client Sanitization**: Path traversal characters (`..`, `/`, `\`) and ground-truth label fields are blocked before submission.
- **No Secrets**: No API keys, credentials, or filesystem paths are stored or transmitted by the client.

---

## 12. Accessibility (a11y)
- Semantic HTML tags (`<header>`, `<main>`, `<nav>`, `<footer>`, `<dialog>`, `<button>`).
- ARIA attributes (`role="region"`, `role="alert"`, `role="status"`, `aria-modal="true"`, `aria-label`).
- Keyboard navigable buttons and accessible focus outlines.
- Multi-dimensional status communication: States communicate via color, distinct icons, text badges, and labels (never color alone).
- Motion preference: Full support for `@media (prefers-reduced-motion: reduce)`.

---

## 13. Testing
The test suite consists of 50 Vitest / React Testing Library tests across 4 test suites:
- `components.test.tsx` (26 tests): Validates atomic UI components, badge variants, and telemetry.
- `markdown.test.tsx` (7 tests): Validates markdown formatting and verifies zero script execution.
- `pages.test.tsx` (6 tests): Validates page rendering, navigation, and API status probing.
- `integration.test.tsx` (11 tests): End-to-end integration tests for HDFS analysis, BGL safety case, claim filtering, citation inspection, error handling, and duplicate submission prevention.

---

## 14. Build Verification
- TypeScript typecheck: `npm run typecheck` (`tsc --noEmit`) passes with 0 errors.
- ESLint: `npm run lint` passes with 0 warnings and 0 errors.
- Production bundle: `npm run build` compiles 58 modules into optimized distribution chunks in under 20s.

---

## 15. Environment Configuration
Configuration is managed via Vite environment variables:
- `VITE_API_BASE_URL`: Base URL of the Phase 10 FastAPI serving backend (default: `http://localhost:8000`).
- Documented in [`.env.example`](file:///d:/FaultSentinel/frontend/.env.example). `.env` files and credentials are excluded via `.gitignore`.

---

## 16. Phase 10 Dependency
The dashboard depends strictly on the Phase 10 API contracts:
- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1`
- `POST /api/v1/analyze`

---

## 17. Phase 12 Interface
Phase 12 will implement Evaluation & Benchmarking. The Phase 11 dashboard does not replace the scientific evaluation pipeline and does not display synthetic benchmark leaderboards. When Phase 12 produces frozen evaluation results, those will be ingested through dedicated evaluation contracts.

---

## 18. Limitations
- **Stateless Session**: The dashboard maintains analysis results in React component memory; it does not persist incident history to a database.
- **Single-Tenant Review**: Does not implement multi-user collaboration, assigned review queues, or role-based access control.
- **No Notification Subsystem**: Alerting, email/Slack webhooks, and paging integrations belong to later operational phases.
