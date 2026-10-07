# SentinelLog Dependency Security & Supply Chain Integrity (Phase 14)

## 1. Dependency Discipline & Pinning (Rule 5)

SentinelLog strictly abides by minimal, reproducible dependency management:
- **Python Dependencies:** Declared and locked via `requirements.txt`. No unapproved floating runtime dependencies are permitted.
- **Frontend Dependencies:** Locked via `frontend/package-lock.json`. Every dependency and transitive package hash is verified against official npm registry signatures.
- **No Install-Time Scripts:** Custom pre/post install scripts that could introduce supply-chain risks are prohibited.

## 2. Dependency Audit Methodology

Dependencies are inventoried and audited against standard vulnerability feeds:
- Python dependencies inspected using `pip list` and vulnerability advisory databases.
- Node.js dependencies audited via `npm audit --omit=dev`.

### Audit Findings Summary
- Total Python Packages: 24 direct & indirect runtime packages.
- Total Frontend Packages: 198 packages in lockfile.
- Known Critical / High Remote Code Execution (RCE) Vulnerabilities: **0**.
- Complete audit inventory and assessment is documented in `results/phase14/dependency_audit.json`.

## 3. Accepted Risks Register

| Dependency | Component | Advisory | Severity | Status | Mitigation / Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pydantic` / `fastapi` | Backend | None | None | Clean | Up-to-date stable versions pinned in venv. |
| `scikit-learn` / `numpy` | Scientific ML | None | None | Clean | Authoritative Phase 4-8 models pinned; test evaluations frozen. |
| `vite` / `lucide-react` | Frontend | None | None | Clean | Pinned in package-lock.json. Static assets served in browser. |
