# FaultSentinel — Frontend Command Center

**Calibrated AI Incident Triage & Evidence-Grounded Root Cause Analysis**

FaultSentinel is an AI-assisted incident intelligence command center designed for SREs, reliability teams, and platform engineers. It provides a calibrated, selective prediction cascade over high-throughput operational log streams.

---

## Architecture Hierarchy

```
RAW LOGS
   ↓
DRAIN3 PARSING
   ↓
WINDOW CONSTRUCTION
   ↓
FEATURE EXTRACTION
   ↓
ANOMALY SCORING (B0 / B1 / B2)
   ↓
CONFORMAL SELECTIVE GATE (Target Risk α)
   ↙                              ↘
AUTO-CLEAR                   ESCALATE
                                  ↓
                             HISTORICAL RETRIEVAL
                                  ↓
                             MMR EVIDENCE SELECTION
                                  ↓
                             DETERMINISTIC REASONING
                                  ↓
                             LLM EXPLANATION
                                  ↓
                             FAITHFULNESS VERIFICATION
                                  ↓
                             VERIFIED INCIDENT OUTPUT
```

> **Design Principle**: FaultSentinel is **not a chatbot**. The LLM is an explanation component strictly downstream of the deterministic detection and conformal escalation pipeline.

---

## Design System

The command center uses a disciplined, restrained **Black, Grayscale, and Semantic Accent** visual system:

- **Background:** `#050505`
- **Primary Surfaces:** `#0A0A0A`
- **Secondary Surfaces:** `#101010`
- **Elevated Surfaces:** `#151515`
- **Borders:** `#242424` (subtle: `#1A1A1A`)
- **Typography:** Inter (Sans), JetBrains Mono (Monospace for latencies, scores, thresholds, and log lines)
- **Semantic Accents:**
  - Success / Verified: `#22C55E`
  - Warning / Alert: `#F59E0B`
  - Critical / Incident: `#EF4444`
  - Info / Metadata: `#60A5FA`

---

## Workspace Navigation

The desktop-first application shell (236px fixed sidebar) provides 10 specialized operational workspaces:

1. **Overview / Command Center (`/`)**: Executive telemetry, 4 core KPI metric cards with sparklines, interactive 7-stage Triage Pipeline hero, and architecture topology.
2. **Live Triage (`/analyze`)**: Dense 3-column operational investigation workspace with line-numbered Log Viewer, Anomaly / Conformal Decision Card, Vertical Decision Trace, Evidence Panel, and Verified Incident Assessment.
3. **Incidents (`/incidents`)**: Searchable, filterable audit table with severity badges, conformal decisions, faithfulness statuses, and deep-dive drawer.
4. **Anomaly Explorer (`/explorer`)**: Black & white chronological score chart with conformal threshold and escalation points.
5. **Explanations / Review (`/review`)**: Evidence register, claim-level faithfulness auditor, and operator verification workflow.
6. **Evaluation Lab (`/evaluation`)**: Scientific benchmarking dashboard visualizing Precision vs Coverage, Empirical Selective Risk vs Target $\alpha$, and baseline comparisons (B0, B1, B2, B3, Proposed) using verified Phase 12 evaluation artifacts.
7. **Cost Intelligence (`/cost`)**: Selective escalation efficiency tracking (94.78% compute reduction proxy, LLM calls avoided vs windows processed).
8. **Model Observatory (`/models`)**: Health, version, and latency waterfall across all 9 pipeline subsystems.
9. **Architecture (`/architecture`)**: Interactive pipeline topology graph with technical inspector drawer for each subsystem.
10. **Configuration (`/status`)**: System health, candidate SLIs, and runtime diagnostics mapped to `/api/v1/diagnostics`.

---

## Development & Verification

### Prerequisites
- Node.js 18+
- npm 9+

### Commands

```powershell
# Install dependencies
npm install

# Run development server (Vite)
npm run dev

# Run unit and integration tests (Vitest)
npm test

# Typecheck TypeScript without emitting code
npm run typecheck

# Lint with ESLint
npm run lint

# Production build
npm run build
```

---

## Safety & Data Integrity Guarantees

1. **Test Set Protection (Rule 1)**: The frontend never accesses or requests `data/test/`.
2. **No Fabricated Data (Rule 7)**: Evaluation benchmarks stem directly from verified Phase 12 execution artifacts (`results/phase12/eval_metrics_hdfs.json`). Unmeasured values are clearly marked `TBD` or `Awaiting evaluation`.
3. **Interactive Evidence Grounding**: Every citation in the Verified Incident Assessment is clickable and cross-references source line numbers in the log viewer.
4. **Zero Client Secrets**: No API keys or LLM tokens are bundled or exposed client-side.
