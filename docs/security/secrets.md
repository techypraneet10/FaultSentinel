# SentinelLog Secret Management & Scanning (Phase 14)

## 1. Zero-Secrets Policy

SentinelLog enforces a strict zero-secrets policy across the codebase:
1. **Never Commit Secrets:** API keys, cloud tokens, database credentials, and private keys must never exist in git-tracked files.
2. **Configuration via Environment:** All secrets must be supplied at runtime through environment variables (`SENTINELLOG_API_KEY`) or mounted volume files.
3. **Template Placeholders Only:** Committed templates (`.env.example`, `configs/security.example.yaml`) contain obvious placeholders (`CHANGE_ME_IN_PRODUCTION...`).

## 2. Automated Repository Secret Scanning

A deterministic scanner is implemented in `sentinellog.security.secret_scanner` and executed as part of automated CI verification.

### Detected Signatures
- **AWS Access Keys:** Regex pattern matching `AKIA...`, `ASIA...` (20-character key IDs).
- **GitHub Tokens:** `ghp_...`, `gho_...`, `ghs_...` patterns.
- **Private Key Headers:** `-----BEGIN RSA/OPENSSH/PGP PRIVATE KEY-----`.
- **Generic Bearer Tokens:** High-entropy Bearer token strings.
- **Hardcoded Credential Assignments:** Code assignments like `api_key = "..."`.

### Verification Command
```bash
python -c "from sentinellog.security.secret_scanner import scan_repository; findings = scan_repository('.'); assert len(findings) == 0, f'Secrets found: {findings}'"
```

## 3. Redaction & Output Sanitization

SentinelLog observability and error-handling pipelines enforce runtime secret sanitization:
- `Authorization` and `X-API-Key` headers are stripped from logs and diagnostic traces.
- Exception handlers map internal errors to fixed codes without exposing system variables, paths, or exception kwargs.
- Prometheus metrics (`/metrics`) use bounded string enumerations and never expose user tokens or raw request bodies.
